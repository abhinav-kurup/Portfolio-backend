Looking at your code, you have a solid hybrid RAG pipeline. Let me show you how to layer a knowledge graph on top of it with minimal disruption.
Your Current Flow vs Graph-Enhanced Flow
Current:  Query → Vector + FTS → Chunks → LLM
Enhanced: Query → Entity Extract → Graph Traversal + Vector + FTS → Richer Chunks → LLM
Step 1: Schema — Add Graph Tables to your SQLite DB
sql-- migrations/add_knowledge_graph.sql

-- Entities extracted from documents
CREATE TABLE IF NOT EXISTS kg_entities (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    type      TEXT,                -- e.g. "PERSON", "PROJECT", "SKILL", "TECHNOLOGY"
    doc_id    INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(name, doc_id)
);

-- Directed relationships between entities
CREATE TABLE IF NOT EXISTS kg_relations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id  INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    predicate   TEXT NOT NULL,     -- e.g. "built", "uses", "worked_at", "knows"
    object_id   INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    doc_id      INTEGER REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kg_relations_subject ON kg_relations(subject_id);
CREATE INDEX IF NOT EXISTS idx_kg_relations_object  ON kg_relations(object_id);
CREATE INDEX IF NOT EXISTS idx_kg_entities_name     ON kg_entities(name);
Step 2: Graph Builder — Extract Entities & Relations at Ingest Time
Create app/services/knowledge_graph/builder.py:
pythonfrom __future__ import annotations

import json
import re
from sqlite3 import Connection

from app.clients.anthropic import anthropic_client  # your existing LLM client
from app.core.logging import setup_logging

logger = setup_logging()

EXTRACTION_PROMPT = """
Extract entities and relationships from the text below.

Return ONLY valid JSON (no markdown, no explanation):
{
  "entities": [
    {"name": "...", "type": "PERSON|SKILL|PROJECT|TECHNOLOGY|COMPANY|OTHER"}
  ],
  "relations": [
    {"subject": "...", "predicate": "...", "object": "..."}
  ]
}

Rules:
- Entity names must be exact strings from the text
- Predicates should be lowercase verbs: "uses", "built", "works_at", "knows", "led"
- Only extract high-confidence triples

Text:
{text}
"""


def extract_graph(text: str) -> dict:
    """Call LLM to extract entities + relations from a document chunk."""
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.format(text=text[:3000])  # cap tokens
        }]
    )
    raw = response.content[0].text
    clean = re.sub(r"```json|```", "", raw).strip()
    return json.loads(clean)


def index_document_graph(doc_id: int, content: str, db: Connection) -> None:
    """
    Extract and store graph triples for a document.
    Call this from your existing document ingest pipeline.
    """
    try:
        graph = extract_graph(content)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Graph extraction failed for doc {doc_id}: {e}")
        return

    entity_name_to_id: dict[str, int] = {}

    # Upsert entities
    for ent in graph.get("entities", []):
        name = ent["name"].strip()
        etype = ent.get("type", "OTHER")
        if not name:
            continue

        cursor = db.execute(
            """
            INSERT INTO kg_entities (name, type, doc_id)
            VALUES (?, ?, ?)
            ON CONFLICT(name, doc_id) DO UPDATE SET type = excluded.type
            RETURNING id
            """,
            [name, etype, doc_id],
        )
        row = cursor.fetchone()
        if row:
            entity_name_to_id[name] = row["id"]

    # Insert relations
    for rel in graph.get("relations", []):
        subj_id = entity_name_to_id.get(rel["subject"])
        obj_id  = entity_name_to_id.get(rel["object"])
        if not subj_id or not obj_id:
            continue  # skip if entity wasn't found

        db.execute(
            """
            INSERT OR IGNORE INTO kg_relations (subject_id, predicate, object_id, doc_id)
            VALUES (?, ?, ?, ?)
            """,
            [subj_id, rel["predicate"], obj_id, doc_id],
        )

    db.commit()
    logger.info(
        f"Indexed graph for doc {doc_id}: "
        f"{len(entity_name_to_id)} entities, {len(graph.get('relations', []))} relations"
    )
Step 3: Graph Retriever — Traverse at Query Time
Create app/services/knowledge_graph/retriever.py:
pythonfrom __future__ import annotations

from sqlite3 import Connection

from app.core.logging import setup_logging

logger = setup_logging()


def extract_query_entities(query: str, db: Connection) -> list[int]:
    """
    Simple entity lookup: find kg_entities whose name appears in the query.
    (You can upgrade this to NER or embedding similarity later.)
    """
    words = query.lower().split()
    rows = db.execute(
        "SELECT id, name FROM kg_entities"
    ).fetchall()

    matched_ids = []
    for row in rows:
        if row["name"].lower() in query.lower():
            matched_ids.append(row["id"])
            logger.debug(f"  [KG] Matched entity: {row['name']} (id={row['id']})")

    return matched_ids


def get_related_doc_ids(
    entity_ids: list[int],
    db: Connection,
    hops: int = 2,
) -> set[int]:
    """
    Walk the graph up to `hops` levels from seed entities.
    Returns the set of doc_ids connected to discovered entities.
    """
    if not entity_ids:
        return set()

    visited_entities: set[int] = set(entity_ids)
    frontier: set[int] = set(entity_ids)

    for _ in range(hops):
        if not frontier:
            break

        placeholders = ",".join("?" * len(frontier))
        rows = db.execute(
            f"""
            SELECT DISTINCT
                CASE WHEN subject_id IN ({placeholders}) THEN object_id
                     ELSE subject_id END AS neighbor_id
            FROM kg_relations
            WHERE subject_id IN ({placeholders})
               OR object_id  IN ({placeholders})
            """,
            [*frontier, *frontier, *frontier],
        ).fetchall()

        next_frontier = set()
        for row in rows:
            nid = row["neighbor_id"]
            if nid not in visited_entities:
                visited_entities.add(nid)
                next_frontier.add(nid)

        frontier = next_frontier

    # Get all doc_ids linked to discovered entities
    if not visited_entities:
        return set()

    placeholders = ",".join("?" * len(visited_entities))
    doc_rows = db.execute(
        f"SELECT DISTINCT doc_id FROM kg_entities WHERE id IN ({placeholders})",
        list(visited_entities),
    ).fetchall()

    doc_ids = {row["doc_id"] for row in doc_rows if row["doc_id"]}
    logger.info(f"[KG] Graph traversal found {len(doc_ids)} related docs from {len(entity_ids)} seed entities")
    return doc_ids


def get_graph_context_string(entity_ids: list[int], db: Connection) -> str:
    """
    Format discovered triples as a readable string to inject into the LLM prompt.
    """
    if not entity_ids:
        return ""

    placeholders = ",".join("?" * len(entity_ids))
    rows = db.execute(
        f"""
        SELECT
            es.name AS subject,
            r.predicate,
            eo.name AS object
        FROM kg_relations r
        JOIN kg_entities es ON es.id = r.subject_id
        JOIN kg_entities eo ON eo.id = r.object_id
        WHERE r.subject_id IN ({placeholders})
           OR r.object_id  IN ({placeholders})
        LIMIT 30
        """,
        [*entity_ids, *entity_ids],
    ).fetchall()

    if not rows:
        return ""

    lines = [f"- {row['subject']} → {row['predicate']} → {row['object']}" for row in rows]
    return "Knowledge Graph Facts:\n" + "\n".join(lines)
Step 4: Update retrieval.py — Boost Graph-Connected Docs
In your existing retrieve_context, add graph boosting after fusion:
python# app/services/chat/retrieval.py  (additions only)

from app.services.knowledge_graph.retriever import (
    extract_query_entities,
    get_related_doc_ids,
)

GRAPH_BOOST = 0.15   # add this to hybrid score for graph-connected docs

def retrieve_context(
    query: str,
    db: Connection,
    limit: int = 3,
) -> list[RetrievedChunk]:
    # ... your existing code unchanged until the merging loop ...

    # --- NEW: get graph-connected doc ids ---
    seed_entity_ids = extract_query_entities(query, db)
    graph_doc_ids   = get_related_doc_ids(seed_entity_ids, db)

    for doc_id in candidate_ids:
        semantic = semantic_results.get(doc_id, {}).get("score", 0.0)
        lexical  = lexical_scores.get(doc_id, 0.0)
        # ... existing doc fetch logic ...

        hybrid_score = (SEMANTIC_WEIGHT * semantic) + (LEXICAL_WEIGHT * lexical)

        # --- NEW: boost docs connected via the knowledge graph ---
        if doc_id in graph_doc_ids:
            hybrid_score = min(1.0, hybrid_score + GRAPH_BOOST)
            logger.debug(f"  [KG Boost] doc_id={doc_id} boosted to {hybrid_score:.4f}")

        doc["score"] = round(hybrid_score, 4)
        merged[doc_id] = doc

    ranked = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:limit]
Step 5: Update pipeline.py — Inject Graph Facts into Prompt
python# app/services/chat/pipeline.py  (additions only)

from app.services.knowledge_graph.retriever import (
    extract_query_entities,
    get_graph_context_string,
)

def run_chat_pipeline(payload: ChatRequest, db: Connection) -> ChatResponse:
    # ... your existing code until context building ...

    context = "\n\n".join(
        f"[SOURCE: {chunk['title']}]\n{chunk['content']}"
        for chunk in chunks
    )

    # --- NEW: append graph facts to context ---
    seed_entity_ids = extract_query_entities(query, db)
    graph_facts = get_graph_context_string(seed_entity_ids, db)
    if graph_facts:
        context = graph_facts + "\n\n" + context

    response = generate_answer(query, context)
    # ... rest unchanged ...
Step 6: Wire into Your Ingest Pipeline
Wherever you currently insert documents into the documents table, add one call:
pythonfrom app.services.knowledge_graph.builder import index_document_graph

# after inserting doc and getting doc_id back:
index_document_graph(doc_id=doc_id, content=doc_content, db=db)

What You Get After This
SignalBeforeAfterSemantic similarity✅✅Keyword match (BM25)✅✅Entity relationship boost❌✅Graph facts in prompt❌✅
The changes are additive — your existing vector + FTS logic is untouched, and the graph layer just boosts and enriches on top of it. Start with hops=1 and tune GRAPH_BOOST based on your retrieval quality.You said: Currently this is hopw i seed data# app/db/seed.py

import json
from app.db.connection import get_connection
from app.core.logging import setup_logging

logger = setup_logging()

def is_empty(conn) -> bool:
    row = conn.execute("SELECT COUNT(*) as count FROM documents").fetchone()
    return row["count"] == 0

def run_seed():
    conn = get_connection()
    try:
        if not is_empty(conn):
            logger.info("Database already seeded, skipping.")
            return

        logger.info("Database empty, running initial seed...")

        # import here to avoid circular imports at module level
        from .scripts.seed_data import seed_faq, seed_documents
        seed_faq(conn)
        seed_documents(conn)
        conn.commit()

        logger.info("Initial seed complete.")
    finally:
        conn.close()Currently this is hopw i seed data how to update thisShow more2:08 AMClaude responded: You just need to call indexdocumentgraph after each document is inserted in your seed_documents function.You just need to call index_document_graph after each document is inserted in your seed_documents function. Show me that function and I'll give you the exact update needed.