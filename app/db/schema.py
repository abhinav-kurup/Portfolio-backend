# app/db/schema.py

from __future__ import annotations

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


CONTACT_TABLE = f"""
CREATE TABLE IF NOT EXISTS contact_messages (
    {BASE_FIELDS},
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new'
);
"""


FAQ_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_faq_created_at
ON faq(created_at);
"""


DOCUMENT_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_documents_type
ON documents(doc_type);

CREATE INDEX IF NOT EXISTS idx_documents_created_at
ON documents(created_at);
"""


BLOG_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_blogs_slug
ON blogs(slug);

CREATE INDEX IF NOT EXISTS idx_blogs_published
ON blogs(published);
"""


CONTACT_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_contact_status
ON contact_messages(status);

CREATE INDEX IF NOT EXISTS idx_contact_created_at
ON contact_messages(created_at);
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
    content='documents',
    content_rowid='id'
);
"""


DOC_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS doc_fts_ai
AFTER INSERT ON documents
BEGIN
    INSERT INTO doc_fts(rowid, title, content)
    VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS doc_fts_ad
AFTER DELETE ON documents
BEGIN
    INSERT INTO doc_fts(doc_fts, rowid, title, content)
    VALUES ('delete', old.id, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS doc_fts_au
AFTER UPDATE ON documents
BEGIN
    INSERT INTO doc_fts(doc_fts, rowid, title, content)
    VALUES ('delete', old.id, old.title, old.content);

    INSERT INTO doc_fts(rowid, title, content)
    VALUES (new.id, new.title, new.content);
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

CREATE TRIGGER IF NOT EXISTS contact_set_updated_at
AFTER UPDATE ON contact_messages
BEGIN
    UPDATE contact_messages
    SET updated_at = datetime('now')
    WHERE id = old.id;
END;
"""


SCHEMA_SQL = "\n".join(
    [
        FAQ_TABLE,
        DOCUMENTS_TABLE,
        BLOGS_TABLE,
        CONTACT_TABLE,
        FAQ_INDEXES,
        DOCUMENT_INDEXES,
        BLOG_INDEXES,
        CONTACT_INDEXES,
        FAQ_VEC,
        DOC_VEC,
        DOC_FTS,
        DOC_FTS_TRIGGERS,
        UPDATED_AT_TRIGGERS,
    ]
)


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()