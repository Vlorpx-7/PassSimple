"""Database schema constants: DDL, schema version, and migrations."""

_SCHEMA_VERSION: int = 2

# DDL for the current schema. IF NOT EXISTS makes this safe to run on reopens.
# Existing DBs upgraded from V1 get is_favorite via _MIGRATIONS, not this DDL
# (CREATE TABLE IF NOT EXISTS skips the statement when the table already exists).
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
        updated_at  TEXT NOT NULL,
        is_favorite INTEGER NOT NULL DEFAULT 0
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

# One entry per schema version bump; each value is a single valid SQLite statement.
_MIGRATIONS: dict[int, str] = {
    2: "ALTER TABLE entries ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0;",
}
