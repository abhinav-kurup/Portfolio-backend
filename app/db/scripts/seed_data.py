# scripts/seed_data.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from app.db.connection import get_connection
from app.clients.embeddings import embeddings_client
from app.utils.hashing import get_hash
from app.utils.similarity import serialize_vector

def seed_faq(conn):
    print("Seeding FAQ...")

    file_path = "data/seed/faq.json"
    if not os.path.exists(file_path):
        print(f"  Warning: {file_path} not found. Skipping FAQ seeding.")
        return

    with open(file_path) as f:
        faqs = json.load(f)

    conn.execute("DELETE FROM faq")
    conn.execute("DELETE FROM faq_vec")

    for faq in faqs:
        # 1. Insert into faq table
        cursor = conn.execute("""
            INSERT INTO faq (question, answer)
            VALUES (?, ?)
        """, (faq["question"], faq["answer"]))
        
        faq_id = cursor.lastrowid

        # 2. Embed and insert into faq_vec
        vector = embeddings_client.embed(faq["question"])
        conn.execute("""
            INSERT INTO faq_vec (faq_id, embedding)
            VALUES (?, ?)
        """, (faq_id, serialize_vector(vector)))

        print(f"  FAQ: {faq['question'][:50]}...")

    print(f"  Done — {len(faqs)} FAQ entries seeded.")


def seed_documents(conn):
    print("Seeding documents...")

    file_path = "data/seed/documents.json"
    if not os.path.exists(file_path):
        print(f"  Warning: {file_path} not found. Skipping document seeding.")
        return

    with open(file_path) as f:
        documents = json.load(f)

    for doc in documents:
        new_hash = get_hash(doc["content"])

        existing = conn.execute("""
            SELECT id, content_hash FROM documents
            WHERE doc_type = ? AND title = ?
        """, (doc["doc_type"], doc["title"])).fetchone()

        if existing and existing["content_hash"] == new_hash:
            print(f"  Skipped (unchanged): {doc['title']}")
            continue

        vector = embeddings_client.embed(doc["content"])

        if existing:
            # update existing document
            conn.execute("""
                UPDATE documents
                SET content = ?, metadata = ?, content_hash = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (
                doc["content"],
                json.dumps(doc.get("metadata", {})),
                new_hash,
                existing["id"]
            ))

            conn.execute("""
                UPDATE doc_vec
                SET embedding = ?
                WHERE doc_id = ?
            """, (serialize_vector(vector), existing["id"]))

            print(f"  Updated: {doc['title']}")

        else:
            # insert new document
            cursor = conn.execute("""
                INSERT INTO documents (doc_type, title, content, metadata, content_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doc["doc_type"],
                doc["title"],
                doc["content"],
                json.dumps(doc.get("metadata", {})),
                new_hash
            ))

            doc_id = cursor.lastrowid

            conn.execute("""
                INSERT INTO doc_vec (doc_id, embedding)
                VALUES (?, ?)
            """, (doc_id, serialize_vector(vector)))

            print(f"  Inserted: {doc['title']}")

    print("  Done — documents seeded.")


if __name__ == "__main__":
    conn = get_connection()

    try:
        seed_faq(conn)
        seed_documents(conn)
        conn.commit()
        print("\nAll done.")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise

    finally:
        conn.close()