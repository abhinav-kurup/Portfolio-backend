# app/db/seed.py

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
        conn.close()