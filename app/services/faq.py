from __future__ import annotations

from sqlite3 import Connection

from app.clients.embeddings import embeddings_client
from app.utils.similarity import serialize_vector


from app.models.chat import FAQMatch
from app.core.logging import setup_logging

logger = setup_logging()

FAQ_SIMILARITY_THRESHOLD = 0.88


def find_faq_match(query: str, db: Connection) -> FAQMatch | None:
    """
    First-pass semantic FAQ lookup.

    Flow:
    1. Embed user query
    2. Compare against faq_vec
    3. Fetch best FAQ row
    4. Return direct answer if above threshold
    """
    query_vec = embeddings_client.embed(query)
    serialized_vec = serialize_vector(query_vec)

    row = db.execute(
        """
        SELECT
            f.id,
            f.question,
            f.answer,
            vec_distance_cosine(fv.embedding, ?) AS score
        FROM faq_vec fv
        JOIN faq f ON f.id = fv.faq_id
        ORDER BY score ASC
        LIMIT 1
        """,
        [serialized_vec],
    ).fetchone()

    if not row:
        logger.info("No FAQ candidates found in database.")
        return None

    similarity = 1 - row["score"]
    logger.info(f"Best FAQ match: '{row['question']}' | Similarity: {round(similarity, 4)} (Threshold: {FAQ_SIMILARITY_THRESHOLD})")

    if similarity < FAQ_SIMILARITY_THRESHOLD:
        logger.info("FAQ similarity below threshold, proceeding to full retrieval.")
        return None

    logger.info("FAQ match found, returning direct answer.")
    return {
        "id": row["id"],
        "question": row["question"],
        "answer": row["answer"],
        "score": round(similarity, 4),
    }