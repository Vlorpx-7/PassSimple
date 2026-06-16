"""SQLite schema, migrations, and CRUD operations for the vault."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.models import Entry, Tag


def get_db_path() -> Path:
    """Return the platform-conventional path for vault.db."""
    raise NotImplementedError


def open_db(path: Path | None = None) -> sqlite3.Connection:
    """Open (and initialise/migrate) the vault database. Returns a connection."""
    raise NotImplementedError


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they do not exist."""
    raise NotImplementedError


# --- vault_meta ---

def get_meta(conn: sqlite3.Connection, key: str) -> bytes | None:
    """Read a raw BLOB from vault_meta by key."""
    raise NotImplementedError


def set_meta(conn: sqlite3.Connection, key: str, value: bytes) -> None:
    """Insert or replace a BLOB in vault_meta."""
    raise NotImplementedError


# --- entries ---

def create_entry(conn: sqlite3.Connection, entry: Entry) -> int:
    """Insert a new entry; returns the new row id."""
    raise NotImplementedError


def get_entry(conn: sqlite3.Connection, entry_id: int) -> Entry | None:
    """Fetch a single entry by id."""
    raise NotImplementedError


def update_entry(conn: sqlite3.Connection, entry: Entry) -> None:
    """Update all fields of an existing entry."""
    raise NotImplementedError


def delete_entry(conn: sqlite3.Connection, entry_id: int) -> None:
    """Delete an entry and its tag associations."""
    raise NotImplementedError


def list_entries(conn: sqlite3.Connection, search: str = "") -> list[Entry]:
    """Return all entries, optionally filtered by title/username substring."""
    raise NotImplementedError


# --- tags ---

def get_or_create_tag(conn: sqlite3.Connection, name: str) -> Tag:
    """Return an existing tag or create a new one."""
    raise NotImplementedError


def set_entry_tags(conn: sqlite3.Connection, entry_id: int, tags: list[Tag]) -> None:
    """Replace all tags for an entry."""
    raise NotImplementedError
