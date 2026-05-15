# app/db/schema.py

from __future__ import annotations
from app.db.connection import get_connection
import sqlite3


BASE_FIELDS = """
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
"""


FAQ_TABLE = f"""
CREATE TABLE IF NOT EXISTS faq (
    {BASE_FIELDS},
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    metadata TEXT DEFAULT '{{}}'
);
"""


DOCUMENTS_TABLE = f"""
CREATE TABLE IF NOT EXISTS documents (
    {BASE_FIELDS},
    doc_type TEXT NOT NULL,              -- skill / project / experience
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_path TEXT,
    content_hash TEXT,
    metadata TEXT DEFAULT '{{}}'
);
"""


BLOGS_TABLE = f"""
CREATE TABLE IF NOT EXISTS blogs (
    {BASE_FIELDS},
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    cover_image TEXT,
    published INTEGER NOT NULL DEFAULT 1,
    metadata TEXT DEFAULT '{{}}'
);
"""

FAQ_VEC = """
CREATE VIRTUAL TABLE IF NOT EXISTS faq_vec
USING vec0(
    faq_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);
"""


DOC_VEC = """
CREATE VIRTUAL TABLE IF NOT EXISTS doc_vec
USING vec0(
    doc_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);
"""


DOC_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts
USING fts5(
    title,
    content,
    metadata,
    content='documents',
    content_rowid='id'
);
"""


DOC_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS doc_fts_ai
AFTER INSERT ON documents
BEGIN
    INSERT INTO doc_fts(rowid, title, content, metadata)
    VALUES (new.id, new.title, new.content, new.metadata);
END;

CREATE TRIGGER IF NOT EXISTS doc_fts_ad
AFTER DELETE ON documents
BEGIN
    INSERT INTO doc_fts(doc_fts, rowid, title, content, metadata)
    VALUES ('delete', old.id, old.title, old.content, old.metadata);
END;

CREATE TRIGGER IF NOT EXISTS doc_fts_au
AFTER UPDATE ON documents
BEGIN
    INSERT INTO doc_fts(doc_fts, rowid, title, content, metadata)
    VALUES ('delete', old.id, old.title, old.content, old.metadata);

    INSERT INTO doc_fts(rowid, title, content, metadata)
    VALUES (new.id, new.title, new.content, new.metadata);
END;
"""


UPDATED_AT_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS faq_set_updated_at
AFTER UPDATE ON faq
BEGIN
    UPDATE faq
    SET updated_at = datetime('now')
    WHERE id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS documents_set_updated_at
AFTER UPDATE ON documents
BEGIN
    UPDATE documents
    SET updated_at = datetime('now')
    WHERE id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS blogs_set_updated_at
AFTER UPDATE ON blogs
BEGIN
    UPDATE blogs
    SET updated_at = datetime('now')
    WHERE id = old.id;
END;
"""


# KG_ENTITIES_TABLE = """
# CREATE TABLE IF NOT EXISTS kg_entities (
#     id        INTEGER PRIMARY KEY AUTOINCREMENT,
#     name      TEXT NOT NULL,
#     type      TEXT,                -- e.g. "PERSON", "PROJECT", "SKILL", "TECHNOLOGY"
#     doc_id    INTEGER REFERENCES documents(id) ON DELETE CASCADE,
#     UNIQUE(name, doc_id)
# );
# """

# KG_RELATIONS_TABLE = """
# CREATE TABLE IF NOT EXISTS kg_relations (
#     id          INTEGER PRIMARY KEY AUTOINCREMENT,
#     subject_id  INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
#     predicate   TEXT NOT NULL,     -- e.g. "built", "uses", "worked_at", "knows"
#     object_id   INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
#     doc_id      INTEGER REFERENCES documents(id) ON DELETE CASCADE
# );
# """

# KG_INDICES = """
# CREATE INDEX IF NOT EXISTS idx_kg_relations_subject ON kg_relations(subject_id);
# CREATE INDEX IF NOT EXISTS idx_kg_relations_object  ON kg_relations(object_id);
# CREATE INDEX IF NOT EXISTS idx_kg_entities_name     ON kg_entities(name);
# """

SCHEMA_SQL = "\n".join(
    [
        FAQ_TABLE,
        DOCUMENTS_TABLE,
        BLOGS_TABLE,
        FAQ_VEC,
        DOC_VEC,
        DOC_FTS,
        DOC_FTS_TRIGGERS,
        UPDATED_AT_TRIGGERS,
        # KG_ENTITIES_TABLE,
        # KG_RELATIONS_TABLE,
        # KG_INDICES,
    ]
)


def create_schema() -> None:
       
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    create_schema()