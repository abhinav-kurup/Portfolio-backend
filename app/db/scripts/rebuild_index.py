# scripts/rebuild_index.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.connection import get_connection
from app.clients.embeddings import embeddings_client
from app.utils.similarity import serialize_vector

def rebuild_vectors(conn):
    print("Rebuilding vector index...")

    conn.execute("DELETE FROM documents_vec")

    documents = conn.execute("""
        SELECT id, content FROM documents
    """).fetchall()

    for doc in documents:
        vector = embeddings_client.embed(doc["content"])

        conn.execute("""
            INSERT INTO documents_vec (document_id, embedding)
            VALUES (?, ?)
        """, (doc["id"], serialize_vector(vector)))

        print(f"Re-embedded document id: {doc['id']}")

    print(f"Done — {len(documents)} documents re-embedded.")


if __name__ == "__main__":
    conn = get_connection()

    try:
        rebuild_vectors(conn)
        conn.commit()
        print("\nAll done.")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise

    finally:
        conn.close()