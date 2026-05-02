# app/services/chat/retrieval.py

from __future__ import annotations

from sqlite3 import Connection

from app.clients.embeddings import embeddings_client
from app.utils.similarity import serialize_vector
from app.models.chat import RetrievedChunk


RRF_K = 60


def _vector_search(
    db: Connection,
    query: str,
    top_k: int,
) -> list[RetrievedChunk]:
    """
    Semantic search over doc_vec.
    Returns ranked semantic candidates.
    """
    query_vec = embeddings_client.embed(query)
    serialized_vec = serialize_vector(query_vec)

    rows = db.execute(
        """
        SELECT
            d.id,
            d.title,
            d.content,
            vec_distance_cosine(v.embedding, ?) AS distance
        FROM doc_vec v
        JOIN documents d ON d.id = v.doc_id
        ORDER BY distance ASC
        LIMIT ?
        """,
        [serialized_vec, top_k],
    ).fetchall()

    results: list[RetrievedChunk] = []

    for row in rows:
        similarity = 1.0 - float(row["distance"])
        results.append(
            {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "score": round(similarity, 4),
            }
        )

    return results


def _fts_search(
    db: Connection,
    query: str,
    top_k: int,
) -> list[RetrievedChunk]:
    """
    Keyword search over FTS5.
    Returns ranked lexical candidates.
    """
    import re
    # Clean the query for FTS to avoid syntax errors with special chars like ? or *
    clean_query = re.sub(r'[^\w\s]', ' ', query).strip()
    if not clean_query:
        return []

    rows = db.execute(
        """
        SELECT
            d.id,
            d.title,
            d.content
        FROM doc_fts
        JOIN documents d ON d.id = doc_fts.rowid
        WHERE doc_fts MATCH ?
        LIMIT ?
        """,
        [clean_query, top_k],
    ).fetchall()

    results: list[RetrievedChunk] = []

    for row in rows:
        results.append(
            {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "score": 0.0,  # placeholder, RRF ignores raw score
            }
        )

    return results


def _reciprocal_rank_fusion(
    vector_results: list[RetrievedChunk],
    fts_results: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    """
    Merge ranked lists using Reciprocal Rank Fusion (RRF).

    RRF score:
        1 / (K + rank)

    This avoids forcing cosine similarity and FTS ranking
    into the same score space.
    """
    scores: dict[int, float] = {}
    docs: dict[int, RetrievedChunk] = {}

    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (RRF_K + rank + 1))
        docs[doc_id] = doc

    for rank, doc in enumerate(fts_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (RRF_K + rank + 1))
        docs[doc_id] = doc

    ranked_ids = sorted(scores, key=lambda doc_id: scores[doc_id], reverse=True)

    merged: list[RetrievedChunk] = []
    for doc_id in ranked_ids:
        doc = docs[doc_id]
        doc["score"] = round(scores[doc_id], 4)  # fused score
        merged.append(doc)

    return merged


def retrieve_context(
    query: str,
    db: Connection,
    limit: int = 3,
) -> list[RetrievedChunk]:
    """
    Hybrid retrieval:
    1. semantic search
    2. keyword search
    3. merge via RRF
    4. return top-k
    """
    query = query.strip()
    if not query:
        return []

    top_k = limit * 2  # fetch wider, trim after fusion

    vector_results = _vector_search(db, query, top_k)
    fts_results = _fts_search(db, query, top_k)

    merged = _reciprocal_rank_fusion(vector_results, fts_results)
    return merged[:limit]