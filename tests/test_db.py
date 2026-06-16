"""Tests for src/db.py — schema, CRUD, encryption at rest, tags."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from src.crypto import generate_master_key
from src.db import Vault
from src.models import Entry, Tag


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault(tmp_path: Path) -> Generator[Vault, None, None]:
    """Open Vault backed by a temporary file; close after each test."""
    v = Vault()
    v.open(generate_master_key(), path=tmp_path / "vault.db")
    yield v
    v.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_schema_tables_exist(vault: Vault) -> None:
    """All four tables must be present after open()."""
    tables = {
        r["name"]
        for r in vault._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert {"vault_meta", "entries", "tags", "entry_tags"}.issubset(tables)


def test_schema_version_written_on_first_open(vault: Vault) -> None:
    """schema_version must be 1 in vault_meta after the first open()."""
    row = vault._conn.execute(
        "SELECT value FROM vault_meta WHERE key = ?", ("schema_version",)
    ).fetchone()
    assert row is not None
    assert int(row["value"]) == 1


def test_schema_version_not_duplicated_on_reopen(tmp_path: Path) -> None:
    """Reopening an existing DB must not insert a second schema_version row."""
    key = generate_master_key()
    db = tmp_path / "vault.db"
    v = Vault()
    v.open(key, path=db)
    v.close()
    v2 = Vault()
    v2.open(key, path=db)
    count = v2._conn.execute(
        "SELECT COUNT(*) FROM vault_meta WHERE key = ?", ("schema_version",)
    ).fetchone()[0]
    v2.close()
    assert count == 1


# ---------------------------------------------------------------------------
# Entry CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_entry(vault: Vault) -> None:
    """add_entry / get_entry must roundtrip all fields including decrypted password."""
    eid = vault.add_entry(
        "Gmail",
        "hunter2",
        username="alice@gmail.com",
        url="https://mail.google.com",
        notes="personal",
    )
    entry = vault.get_entry(eid)
    assert entry is not None
    assert entry.id == eid
    assert entry.title == "Gmail"
    assert entry.username == "alice@gmail.com"
    assert entry.url == "https://mail.google.com"
    assert entry.notes == "personal"
    assert entry.password == "hunter2"


def test_get_entry_returns_none_for_missing_id(vault: Vault) -> None:
    """get_entry must return None when the id does not exist."""
    assert vault.get_entry(99999) is None


def test_update_entry_fields(vault: Vault) -> None:
    """update_entry must persist changed title, username, url, notes."""
    eid = vault.add_entry("Old", "pw", username="old_user", url="https://old.example")
    entry = vault.get_entry(eid)
    entry.title = "New"
    entry.username = "new_user"
    entry.url = "https://new.example"
    vault.update_entry(entry)
    updated = vault.get_entry(eid)
    assert updated.title == "New"
    assert updated.username == "new_user"
    assert updated.url == "https://new.example"
    assert updated.password == "pw"  # unchanged


def test_update_entry_new_password(vault: Vault) -> None:
    """update_entry with new_password must re-encrypt and return the new plaintext."""
    eid = vault.add_entry("Site", "old_pw")
    entry = vault.get_entry(eid)
    vault.update_entry(entry, new_password="new_pw")
    assert vault.get_entry(eid).password == "new_pw"


def test_delete_entry_removes_from_get_and_list(vault: Vault) -> None:
    """Deleted entry must not appear in get_entry or list_entries."""
    eid = vault.add_entry("ToDelete", "pw")
    vault.delete_entry(eid)
    assert vault.get_entry(eid) is None
    assert all(e.id != eid for e in vault.list_entries())


def test_list_entries_ordered_by_title(vault: Vault) -> None:
    """list_entries must return entries sorted by title."""
    vault.add_entry("Zebra", "pw")
    vault.add_entry("Apple", "pw")
    vault.add_entry("Mango", "pw")
    titles = [e.title for e in vault.list_entries()]
    assert titles == sorted(titles)


def test_list_entries_does_not_decrypt_password(vault: Vault) -> None:
    """list_entries must not decrypt passwords — entry.password is None for all rows."""
    vault.add_entry("Site", "secret")
    assert all(e.password is None for e in vault.list_entries())


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_search_by_title_substring(vault: Vault) -> None:
    """search_entries must match a title substring case-insensitively."""
    vault.add_entry("GitHub", "pw", username="dev")
    vault.add_entry("GitLab", "pw", username="dev")
    vault.add_entry("Amazon", "pw")
    results = vault.search_entries("git")
    assert len(results) == 2
    assert all("git" in e.title.lower() for e in results)


def test_search_by_username_substring(vault: Vault) -> None:
    """search_entries must match a username substring."""
    vault.add_entry("Site A", "pw", username="alice@example.com")
    vault.add_entry("Site B", "pw", username="bob@example.com")
    results = vault.search_entries("alice")
    assert len(results) == 1
    assert results[0].title == "Site A"


def test_search_no_match_returns_empty(vault: Vault) -> None:
    """search_entries must return an empty list when nothing matches."""
    vault.add_entry("Gmail", "pw")
    assert vault.search_entries("zzznomatch") == []


def test_search_does_not_decrypt_password(vault: Vault) -> None:
    """search_entries must not decrypt passwords."""
    vault.add_entry("Site", "secret")
    assert all(e.password is None for e in vault.search_entries("site"))


# ---------------------------------------------------------------------------
# Encryption at rest  (core security requirement)
# ---------------------------------------------------------------------------


def test_password_not_stored_in_plaintext(vault: Vault, tmp_path: Path) -> None:
    """The password_ct column in the DB file must not contain the plaintext password.

    This bypasses the Vault layer entirely and inspects raw bytes on disk.
    """
    plaintext_pw = "my_super_secret_password_123"
    eid = vault.add_entry("Test", plaintext_pw, username="user")

    # Open a completely separate connection to the same file.
    raw = sqlite3.connect(str(tmp_path / "vault.db"))
    row = raw.execute("SELECT password_ct FROM entries WHERE id = ?", (eid,)).fetchone()
    raw.close()

    blob: bytes = row[0]
    assert isinstance(blob, bytes), "password_ct must be stored as BLOB"
    assert plaintext_pw.encode("utf-8") not in blob, (
        "Plaintext password must never appear verbatim in the stored blob"
    )
    # Sanity: blob is larger than plaintext (nonce 12 B + GCM tag 16 B overhead).
    assert len(blob) > len(plaintext_pw)


def test_reencrypt_produces_different_ciphertext(vault: Vault) -> None:
    """Re-encrypting the same plaintext must yield a different blob (new nonce)."""
    eid = vault.add_entry("Site", "same_password")
    ct1 = vault.get_entry(eid).password_ct
    vault.update_entry(vault.get_entry(eid), new_password="same_password")
    ct2 = vault.get_entry(eid).password_ct
    assert ct1 != ct2


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def test_add_tag_is_idempotent(vault: Vault) -> None:
    """add_tag called twice with the same name must return the same id."""
    t1 = vault.add_tag("work")
    t2 = vault.add_tag("work")
    assert t1.id == t2.id
    assert t1.name == "work"


def test_entry_tags_returned_by_get_entry(vault: Vault) -> None:
    """Tags supplied during add_entry must appear in get_entry results."""
    eid = vault.add_entry("Site", "pw", tag_names=["work", "dev"])
    tag_names = {t.name for t in vault.get_entry(eid).tags}
    assert tag_names == {"work", "dev"}


def test_tag_entry_and_untag_entry(vault: Vault) -> None:
    """tag_entry / untag_entry must add and remove associations correctly."""
    tag = vault.add_tag("personal")
    eid = vault.add_entry("Site", "pw")
    vault.tag_entry(eid, tag.id)
    assert any(t.id == tag.id for t in vault.get_entry(eid).tags)
    vault.untag_entry(eid, tag.id)
    assert not any(t.id == tag.id for t in vault.get_entry(eid).tags)


def test_entries_by_tag_returns_only_matching(vault: Vault) -> None:
    """entries_by_tag must return only entries that carry the given tag."""
    tag = vault.add_tag("finance")
    vault.add_entry("Bank", "pw", tag_names=["finance"])
    vault.add_entry("Email", "pw", tag_names=["personal"])
    results = vault.entries_by_tag(tag.id)
    assert len(results) == 1
    assert results[0].title == "Bank"


def test_delete_entry_cascades_to_entry_tags(vault: Vault) -> None:
    """Deleting an entry must remove its entry_tags rows via ON DELETE CASCADE."""
    tag = vault.add_tag("cascade-test")
    eid = vault.add_entry("ToDelete", "pw", tag_names=["cascade-test"])
    vault.delete_entry(eid)
    # Tag still exists but has no entries.
    assert vault.entries_by_tag(tag.id) == []


def test_update_entry_replaces_tags(vault: Vault) -> None:
    """update_entry must replace the full tag set with the entry's current tags list."""
    eid = vault.add_entry("Site", "pw", tag_names=["old"])
    entry = vault.get_entry(eid)
    entry.tags = [Tag(id=None, name="new")]
    vault.update_entry(entry)
    tag_names = {t.name for t in vault.get_entry(eid).tags}
    assert tag_names == {"new"}


# ---------------------------------------------------------------------------
# Foreign keys
# ---------------------------------------------------------------------------


def test_foreign_key_violation_raises(tmp_path: Path) -> None:
    """Inserting into entry_tags with nonexistent ids must raise IntegrityError.

    Opens a separate raw connection (FK pragma ON) to the same file created by
    Vault, so the schema is guaranteed to exist.
    """
    db = tmp_path / "fk.db"
    v = Vault()
    v.open(generate_master_key(), path=db)
    v.close()

    raw = sqlite3.connect(str(db))
    raw.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute("INSERT INTO entry_tags (entry_id, tag_id) VALUES (?, ?)", (9999, 9999))
        raw.commit()
    raw.close()
