from __future__ import annotations

import re
from sqlite3 import Connection
from app.core.logging import setup_logging

logger = setup_logging()

# Aliases to map common variations to the canonical database names
ALIASES = {
    "cloud": "aws",
    "postgres": "postgresql",
    "js": "javascript",
    "ts": "typescript",
    "crdts": "crdt",
    "websockets": "websocket",
    "neural networks": "llms",
    "large language models": "llms",
    "llm": "llms",
    "ai": "applied ai",
    "doc QA": "document QA",
    "cassandras": "cassandra",
}

# Entity types that trigger graph routing
ROUTING_TYPES = {"TECHNOLOGY", "CONCEPT", "SKILL", "DOMAIN"}


def extract_query_entities(query: str, db: Connection) -> list[int]:
    """
    Deterministic NER matching: Matches query against entities in the database
    using case-insensitive substring and regex word boundaries.
    Only returns entity IDs of types TECHNOLOGY, CONCEPT, SKILL, DOMAIN (graph routing).
    """
    query = query.strip()
    if not query:
        return []

    # 1. Fetch all unique entity names and types from database
    rows = db.execute(
        "SELECT id, name, type FROM kg_entities"
    ).fetchall()

    if not rows:
        return []

    q = query.lower()
    
    # 2. Check for alias matches and rewrite query tokens if needed
    for alias, canonical in ALIASES.items():
        if alias in q:
            q += f" {canonical}"  # Append canonical name to help match it below

    matched_ids = []
    matched_names = []

    # 3. Match each database entity against the query
    for row in rows:
        ent_id = row["id"]
        ent_name = row["name"].lower().strip()
        ent_type = row["type"].upper()

        # Skip matching if the entity type is not one of the routing types
        if ent_type not in ROUTING_TYPES:
            continue

        if not ent_name:
            continue

        # Regex match with word boundaries and support for simple 's' plurals
        pattern = r"\b" + re.escape(ent_name) + r"s?\b"
        if re.search(pattern, q):
            if ent_id not in matched_ids:
                matched_ids.append(ent_id)
                matched_names.append(f"{row['name']} ({ent_type})")

    if matched_names:
        logger.info(f"[KG Routing] Query matched entities: {', '.join(matched_names)}")
    else:
        logger.debug("[KG Routing] Query did not match any routing entities. Skipping graph lookup.")

    return matched_ids


def get_related_doc_ids(
    entity_ids: list[int],
    db: Connection,
    hops: int = 1,
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
