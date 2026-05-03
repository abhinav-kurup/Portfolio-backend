from __future__ import annotations

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
