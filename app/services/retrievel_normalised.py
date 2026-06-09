# app/services/chat/retrieval.py

from __future__ import annotations

from sqlite3 import Connection
import json
import re

from app.clients.embeddings import embeddings_client
from app.utils.similarity import serialize_vector
from app.models.chat import RetrievedChunk
from app.core.logging import setup_logging
from app.services.knowledge_graph.retriever import (
    extract_query_entities,
    get_related_doc_ids,
)
from app.clients.reranker import reranker_client

logger = setup_logging()

SEMANTIC_WEIGHT = 0.7
LEXICAL_WEIGHT = 0.3


def _vector_search(
    db: Connection,
    query: str,
    top_k: int,
) -> dict[int, RetrievedChunk]:
    """
    Semantic search over doc_vec.
    Returns {doc_id: RetrievedChunk} with cosine similarity score.
    """
    query_vec = embeddings_client.embed(query)
    serialized_vec = serialize_vector(query_vec)

    rows = db.execute(
        """
        SELECT
            d.id,
            d.title,
            d.content,
            d.metadata,
            vec_distance_cosine(v.embedding, ?) AS distance
        FROM doc_vec v
        JOIN documents d ON d.id = v.doc_id
        ORDER BY distance ASC
        LIMIT ?
        """,
        [serialized_vec, top_k],
    ).fetchall()

    results: dict[int, RetrievedChunk] = {}

    for row in rows:
        similarity = 1.0 - float(row["distance"])
        metadata_dict = json.loads(row["metadata"]) if row["metadata"] else {}
        results[row["id"]] = {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "metadata": metadata_dict,
            "score": round(similarity, 4),  # semantic score
        }
    
    logger.info(f"Vector search retrieved {len(results)} candidates")
    for doc_id, chunk in results.items():
        logger.debug(f"  [Semantic] ID: {doc_id} | Score: {chunk['score']} | Title: {chunk['title']}")

    return results


def _fts_search(
    db: Connection,
    query: str,
    top_k: int,
) -> dict[int, float]:
    """
    FTS5 keyword search.
    Returns {doc_id: normalized_bm25_score}
    """
    clean_query = re.sub(r'[^\w\s]', ' ', query).strip()
    if not clean_query:
        return {}

    rows = db.execute(
        """
        SELECT
            d.id,
            bm25(doc_fts) AS bm25_score
        FROM doc_fts
        JOIN documents d ON d.id = doc_fts.rowid
        WHERE doc_fts MATCH ?
        ORDER BY bm25_score ASC
        LIMIT ?
        """,
        [clean_query, top_k],
    ).fetchall()

    if not rows:
        return {}

    # bm25: lower is better -> convert to relevance
    raw_scores = [float(row["bm25_score"]) for row in rows]
    min_score = min(raw_scores)
    max_score = max(raw_scores)

    normalized: dict[int, float] = {}

    for row in rows:
        doc_id = row["id"]
        bm25 = float(row["bm25_score"])

        if max_score == min_score:
            lexical_score = 1.0
        else:
            # invert + normalize into [0,1]
            lexical_score = 1.0 - ((bm25 - min_score) / (max_score - min_score))

        normalized[doc_id] = round(lexical_score, 4)
    
    logger.info(f"FTS search retrieved {len(normalized)} candidates")
    for doc_id, score in normalized.items():
        logger.debug(f"  [Lexical] ID: {doc_id} | Score: {score}")

    return normalized


def retrieve_context(
    query: str,
    db: Connection,
    seed_entity_ids: list[int] = None,
    limit: int = 3,
) -> list[RetrievedChunk]:
    """
    Hybrid retrieval with Cross-Encoder reranking:
    1. Semantic search
    2. Lexical search
    3. Graph relationship candidate extraction (metadata-driven)
    4. Reciprocal / Weighted fusion
    5. Top 20 Candidates pass to local Cross-Encoder reranker
    6. Return top-k reranked results
    """
    query = query.strip()
    if not query:
        return []

    # Fetch a wider candidate pool for the reranker to evaluate
    retrieval_k = 15

    semantic_results = _vector_search(db, query, retrieval_k)
    lexical_scores = _fts_search(db, query, retrieval_k)

    # Gather graph candidates based on query routing matching
    if seed_entity_ids is None:
        seed_entity_ids = extract_query_entities(query, db)
    graph_doc_ids = get_related_doc_ids(seed_entity_ids, db)

    # Merge all unique candidate IDs
    candidate_ids = set(semantic_results.keys()) | set(lexical_scores.keys()) | graph_doc_ids

    if not candidate_ids:
        return []

    merged_candidates: list[dict] = []

    # Compile properties and compute initial weighted hybrid score for sorting
    for doc_id in candidate_ids:
        semantic = semantic_results.get(doc_id, {}).get("score", 0.0)
        lexical = lexical_scores.get(doc_id, 0.0)

        if doc_id in semantic_results:
            doc = dict(semantic_results[doc_id])
        else:
            row = db.execute(
                """
                SELECT id, title, content, metadata
                FROM documents
                WHERE id = ?
                """,
                [doc_id],
            ).fetchone()

            if row is None:
                continue

            metadata_dict = json.loads(row["metadata"]) if row["metadata"] else {}
            doc = {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "metadata": metadata_dict,
                "score": 0.0,
            }

        # Weighted hybrid score calculation
        hybrid_score = (SEMANTIC_WEIGHT * semantic) + (LEXICAL_WEIGHT * lexical)
        doc["score"] = round(hybrid_score, 4)
        merged_candidates.append(doc)

    # Sort candidates by hybrid score and select Top 20 for reranker
    merged_candidates.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = merged_candidates[:20]
    
    logger.info(f"Fused retrieval produced {len(merged_candidates)} candidates. Routing top {len(top_candidates)} to Reranker.")

    # Run local Cross-Encoder reranker
    final_results = reranker_client.rerank(query, top_candidates, top_n=limit)
    
    logger.info(f"Final chunks sent to LLM after Cross-Encoder reranking ({len(final_results)}):")
    for doc in final_results:
        logger.info(f"  [Final] ID: {doc['id']} | Score: {doc['score']} | Title: {doc['title']}")
        
    return final_results