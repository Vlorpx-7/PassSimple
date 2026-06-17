"""SQLite-backed vault: schema management and CRUD for entries and tags."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src import crypto
from src.models import Entry, Tag

_SCHEMA_VERSION = 1

# DDL for the initial schema. IF NOT EXISTS makes this safe to run on reopens.
_DDL = """
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


class Vault:
    """Manages the SQLite vault and all entry/tag CRUD.

    Usage::

        vault = Vault()
        vault.open(master_key, path=Path("vault.db"))
        entry_id = vault.add_entry("Gmail", "hunter2", username="alice")
        entry = vault.get_entry(entry_id)   # entry.password == "hunter2"
        vault.close()

    Can also be used as a context manager (calls close() on exit).
    """

    def __init__(self) -> None:
        """Initialise an unopened Vault."""
        self._conn: sqlite3.Connection | None = None
        self._master_key: bytes | None = None

    def __repr__(self) -> str:
        # master_key intentionally absent — safe for logging.
        return f"Vault(open={self._conn is not None})"

    def __enter__(self) -> "Vault":
        """Support the context manager protocol."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close the vault on context exit."""
        self.close()

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    @staticmethod
    def default_path() -> Path:
        """Return the conventional vault path: %LOCALAPPDATA%\\PassSimple\\vault.db."""
        return Path(os.environ["LOCALAPPDATA"]) / "PassSimple" / "vault.db"

    def open(self, master_key: bytes, path: Path | None = None) -> None:
        """Open (and if necessary create) the vault database.

        Creates parent directories automatically. Sets PRAGMA foreign_keys = ON
        and initialises the schema on first use.
        """
        db_path = path if path is not None else Vault.default_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._master_key = master_key
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        # Foreign key enforcement is OFF by default in SQLite — must be set per connection.
        conn.execute("PRAGMA foreign_keys = ON")
        self._conn = conn
        self._init_schema()

    def close(self) -> None:
        """Close the DB connection and clear the master key from memory."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._master_key = None

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _c(self) -> sqlite3.Connection:
        """Return the open connection, or raise if the vault is closed."""
        if self._conn is None:
            raise RuntimeError("Vault is not open — call open() first")
        return self._conn

    def _key(self) -> bytes:
        """Return the master key, or raise if the vault is closed."""
        if self._master_key is None:
            raise RuntimeError("Vault is not open — call open() first")
        return self._master_key

    def _init_schema(self) -> None:
        """Create tables/indexes and record schema_version on first use."""
        conn = self._c()
        # executescript issues an implicit COMMIT before running — that's fine here.
        conn.executescript(_DDL)
        # Insert schema_version only on first open (INSERT OR IGNORE avoids overwriting).
        conn.execute(
            "INSERT OR IGNORE INTO vault_meta (key, value) VALUES (?, ?)",
            ("schema_version", str(_SCHEMA_VERSION).encode()),
        )
        conn.commit()

    @staticmethod
    def _now() -> str:
        """Return the current UTC time as an ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def _ensure_tag(self, name: str) -> int:
        """Insert tag name if absent; return its id. Does NOT commit."""
        conn = self._c()
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        return row["id"]

    def _load_tags(self, entry_id: int) -> list[Tag]:
        """Return all tags associated with entry_id."""
        rows = self._c().execute(
            """
            SELECT t.id, t.name
            FROM   tags t
            JOIN   entry_tags et ON et.tag_id = t.id
            WHERE  et.entry_id = ?
            ORDER  BY t.name
            """,
            (entry_id,),
        ).fetchall()
        return [Tag(id=r["id"], name=r["name"]) for r in rows]

    def _row_to_entry(self, row: sqlite3.Row, *, decrypt: bool) -> Entry:
        """Convert a DB row to Entry, optionally decrypting the password.

        decrypt=True  → entry.password is the plaintext string (used by get_entry).
        decrypt=False → entry.password is None (used by list/search, per
                        "don't hold full vault decrypted in memory").
        """
        password: str | None = None
        if decrypt:
            password = crypto.decrypt(row["password_ct"], self._key())
        return Entry(
            id=row["id"],
            title=row["title"],
            username=row["username"],
            password_ct=row["password_ct"],
            url=row["url"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            tags=self._load_tags(row["id"]),
            password=password,
        )

    # -----------------------------------------------------------------------
    # Entry CRUD
    # -----------------------------------------------------------------------

    def add_entry(
        self,
        title: str,
        password: str,
        *,
        username: str | None = None,
        url: str | None = None,
        notes: str | None = None,
        tag_names: list[str] | None = None,
    ) -> int:
        """Encrypt password and insert a new entry. Returns the new row id."""
        conn = self._c()
        now = self._now()
        password_ct = crypto.encrypt(password, self._key())
        cur = conn.execute(
            """
            INSERT INTO entries (title, username, password_ct, url, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, username, password_ct, url, notes, now, now),
        )
        entry_id = cur.lastrowid
        if tag_names:
            for name in tag_names:
                tag_id = self._ensure_tag(name)
                conn.execute(
                    "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                    (entry_id, tag_id),
                )
        conn.commit()
        return entry_id

    def get_entry(self, entry_id: int) -> Entry | None:
        """Fetch a single entry by id with its password decrypted."""
        row = self._c().execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return None if row is None else self._row_to_entry(row, decrypt=True)

    def update_entry(self, entry: Entry, new_password: str | None = None) -> None:
        """Update all fields of an existing entry.

        Pass new_password to re-encrypt; omit it to keep the current password_ct.
        Tag list on entry replaces all previous tag associations atomically.
        """
        conn = self._c()
        password_ct = (
            crypto.encrypt(new_password, self._key())
            if new_password is not None
            else entry.password_ct
        )
        conn.execute(
            """
            UPDATE entries
            SET title = ?, username = ?, password_ct = ?, url = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (entry.title, entry.username, password_ct, entry.url, entry.notes, self._now(), entry.id),
        )
        conn.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry.id,))
        for tag in entry.tags:
            tag_id = self._ensure_tag(tag.name)
            conn.execute(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                (entry.id, tag_id),
            )
        conn.commit()

    def delete_entry(self, entry_id: int) -> None:
        """Delete an entry; entry_tags rows are removed via ON DELETE CASCADE."""
        conn = self._c()
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()

    def list_entries(self) -> list[Entry]:
        """Return all entries ordered by title. Passwords are NOT decrypted."""
        rows = self._c().execute("SELECT * FROM entries ORDER BY title").fetchall()
        return [self._row_to_entry(r, decrypt=False) for r in rows]

    def search_entries(self, query: str) -> list[Entry]:
        """Case-insensitive substring search over title and username.

        Passwords are NOT decrypted in results — call get_entry for the full record.
        """
        pattern = f"%{query}%"
        rows = self._c().execute(
            """
            SELECT * FROM entries
            WHERE  title    LIKE ?
            OR     username LIKE ?
            ORDER  BY title
            """,
            (pattern, pattern),
        ).fetchall()
        return [self._row_to_entry(r, decrypt=False) for r in rows]

    # -----------------------------------------------------------------------
    # Tag operations
    # -----------------------------------------------------------------------

    def add_tag(self, name: str) -> Tag:
        """Insert tag if absent; return the Tag (existing or new)."""
        conn = self._c()
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        row = conn.execute("SELECT id, name FROM tags WHERE name = ?", (name,)).fetchone()
        conn.commit()
        return Tag(id=row["id"], name=row["name"])

    def tag_entry(self, entry_id: int, tag_id: int) -> None:
        """Associate a tag with an entry (idempotent)."""
        conn = self._c()
        conn.execute(
            "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
            (entry_id, tag_id),
        )
        conn.commit()

    def untag_entry(self, entry_id: int, tag_id: int) -> None:
        """Remove a tag association from an entry."""
        conn = self._c()
        conn.execute(
            "DELETE FROM entry_tags WHERE entry_id = ? AND tag_id = ?",
            (entry_id, tag_id),
        )
        conn.commit()

    def entries_by_tag(self, tag_id: int) -> list[Entry]:
        """Return all entries bearing tag_id, ordered by title. Passwords NOT decrypted."""
        rows = self._c().execute(
            """
            SELECT  e.*
            FROM    entries e
            JOIN    entry_tags et ON et.entry_id = e.id
            WHERE   et.tag_id = ?
            ORDER   BY e.title
            """,
            (tag_id,),
        ).fetchall()
        return [self._row_to_entry(r, decrypt=False) for r in rows]
