"""Tests for src/db.py — schema creation, CRUD, foreign keys."""

import sqlite3

import pytest

from src.db import (
    create_entry,
    delete_entry,
    get_entry,
    get_or_create_tag,
    init_schema,
    list_entries,
    open_db,
    set_entry_tags,
    update_entry,
)
from src.models import Entry, Tag


@pytest.fixture
def conn() -> sqlite3.Connection:
    """Return an in-memory database with the schema initialised."""
    raise NotImplementedError


def test_schema_created(conn: sqlite3.Connection) -> None:
    """Expected tables must exist after init_schema."""
    raise NotImplementedError


def test_create_and_get_entry(conn: sqlite3.Connection) -> None:
    """Create an entry and read it back by id."""
    raise NotImplementedError


def test_update_entry(conn: sqlite3.Connection) -> None:
    """Updating an entry should persist all changed fields."""
    raise NotImplementedError


def test_delete_entry(conn: sqlite3.Connection) -> None:
    """Deleted entry must not be returned by get_entry."""
    raise NotImplementedError


def test_list_entries_search(conn: sqlite3.Connection) -> None:
    """list_entries with a search term should filter by title/username."""
    raise NotImplementedError


def test_tag_cascade_delete(conn: sqlite3.Connection) -> None:
    """Deleting an entry must cascade-delete its entry_tags rows."""
    raise NotImplementedError


def test_foreign_keys_enforced(conn: sqlite3.Connection) -> None:
    """Inserting into entry_tags with a nonexistent entry_id must fail."""
    raise NotImplementedError
