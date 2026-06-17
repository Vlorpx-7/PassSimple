"""Database schema constants: DDL and schema version."""

_SCHEMA_VERSION: int = 1

# DDL for the initial schema. IF NOT EXISTS makes this safe to run on reopens.
_DDL: str = """
    CREATE TABLE IF NOT EXISTS vault_meta (
        key   TEXT PRIMARY KEY,
        value BLOB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS entries (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        username    TEXT,
        password_ct BLOB NOT NULL,
        url         TEXT,
        notes       TEXT,
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_entries_title ON entries (title);
    CREATE TABLE IF NOT EXISTS tags (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS entry_tags (
        entry_id INTEGER REFERENCES entries (id) ON DELETE CASCADE,
        tag_id   INTEGER REFERENCES tags   (id) ON DELETE CASCADE,
        PRIMARY KEY (entry_id, tag_id)
    );
"""
