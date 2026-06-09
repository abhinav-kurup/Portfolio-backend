from __future__ import annotations

import json
from sqlite3 import Connection
from app.core.logging import setup_logging

logger = setup_logging()


def index_document_graph(doc_id: int, db: Connection) -> None:
    """
    Builds the knowledge graph relations deterministically from the document's metadata.
    Does not use LLM calls.
    """
    # 1. Fetch document title, type and metadata
    row = db.execute(
        "SELECT title, doc_type, metadata FROM documents WHERE id = ?", [doc_id]
    ).fetchone()
    
    if not row:
        logger.warning(f"Could not find document with id {doc_id} to index graph.")
        return

    title = row["title"]
    doc_type = row["doc_type"].upper()  # 'PROJECT', 'SKILL', etc.
    
    try:
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
    except Exception as e:
        logger.error(f"Failed to parse metadata JSON for doc {doc_id}: {e}")
        metadata = {}

    # 2. Clean existing entities and relations for this document to support clean updates
    db.execute("DELETE FROM kg_relations WHERE doc_id = ?", [doc_id])
    db.execute("DELETE FROM kg_entities WHERE doc_id = ?", [doc_id])

    # 3. Create the seed/source entity (the project or document itself)
    cursor = db.execute(
        """
        INSERT INTO kg_entities (name, type, doc_id)
        VALUES (?, ?, ?)
        ON CONFLICT(name, doc_id) DO UPDATE SET type = excluded.type
        RETURNING id
        """,
        [title, doc_type, doc_id],
    )
    seed_row = cursor.fetchone()
    if not seed_row:
        logger.error(f"Failed to insert source entity {title} for doc {doc_id}")
        return
        
    seed_entity_id = seed_row["id"]

    # Define mappings of metadata list keys to entity types and relationship predicates
    mappings = [
        ("technologies", "TECHNOLOGY", "uses"),
        ("concepts", "CONCEPT", "involves"),
        ("skills", "SKILL", "demonstrates"),
        ("domains", "DOMAIN", "belongs_to"),
    ]

    entity_count = 0
    relation_count = 0

    # 4. Deterministically populate entities and relations from metadata fields
    for meta_key, entity_type, predicate in mappings:
        items = metadata.get(meta_key, [])
        if not isinstance(items, list):
            if isinstance(items, str) and items.strip():
                items = [items]
            else:
                items = []

        for item in items:
            name = item.strip()
            if not name:
                continue

            # Upsert target entity
            target_cursor = db.execute(
                """
                INSERT INTO kg_entities (name, type, doc_id)
                VALUES (?, ?, ?)
                ON CONFLICT(name, doc_id) DO UPDATE SET type = excluded.type
                RETURNING id
                """,
                [name, entity_type, doc_id],
            )
            target_row = target_cursor.fetchone()
            if not target_row:
                continue
            
            target_entity_id = target_row["id"]
            entity_count += 1

            # Insert relationship link
            db.execute(
                """
                INSERT OR IGNORE INTO kg_relations (subject_id, predicate, object_id, doc_id)
                VALUES (?, ?, ?, ?)
                """,
                [seed_entity_id, predicate, target_entity_id, doc_id],
            )
            relation_count += 1

    db.commit()
    logger.info(
        f"Indexed deterministic graph for doc {doc_id} ('{title}'): "
        f"{entity_count} entities, {relation_count} relations"
    )
