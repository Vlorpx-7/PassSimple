"""Tests for src/importer.py — Chromium CSV parsing."""

from __future__ import annotations

import csv as csv_std
import io
from pathlib import Path

import pytest

from src.importer import ImportError, ImportResult, import_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _csv_file(tmp_path: Path, rows: list[dict[str, str]], *, bom: bool = False) -> Path:
    """Write a Chromium-format CSV to a temp file and return its path."""
    buf = io.StringIO()
    writer = csv_std.DictWriter(
        buf,
        fieldnames=["name", "url", "username", "password", "note"],
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    content = buf.getvalue().encode("utf-8")
    path = tmp_path / "passwords.csv"
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + content)
    return path


# ---------------------------------------------------------------------------
# Well-formed CSV
# ---------------------------------------------------------------------------


def test_valid_csv(tmp_path: Path) -> None:
    """A well-formed Chromium CSV must parse cleanly with all fields mapped."""
    path = _csv_file(
        tmp_path,
        [{"name": "Gmail", "url": "https://mail.google.com", "username": "alice", "password": "hunter2", "note": "personal"}],
    )
    result = import_csv(path)

    assert result.errors == []
    assert len(result.entries) == 1
    e = result.entries[0]
    assert e.title == "Gmail"
    assert e.url == "https://mail.google.com"
    assert e.username == "alice"
    assert e.password == "hunter2"
    assert e.notes == "personal"
    # password_ct must be empty — encryption happens later via Vault
    assert e.password_ct == b""


def test_valid_csv_multiple_rows(tmp_path: Path) -> None:
    """All data rows must be returned as entries when all are well-formed."""
    rows = [
        {"name": f"Site {i}", "url": f"https://site{i}.example", "username": "u", "password": "p", "note": ""}
        for i in range(5)
    ]
    result = import_csv(_csv_file(tmp_path, rows))
    assert len(result.entries) == 5
    assert result.errors == []


# ---------------------------------------------------------------------------
# Missing required columns
# ---------------------------------------------------------------------------


def test_missing_required_columns(tmp_path: Path) -> None:
    """CSV missing the 'password' column must raise ValueError."""
    path = tmp_path / "bad.csv"
    path.write_text("name,url,username\nGmail,https://gmail.com,alice\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        import_csv(path)


def test_missing_multiple_columns_lists_all(tmp_path: Path) -> None:
    """ValueError message must name every missing column."""
    path = tmp_path / "bad.csv"
    path.write_text("name\nGmail\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns") as exc_info:
        import_csv(path)
    msg = str(exc_info.value)
    # url, username, password are all missing
    for col in ("url", "username", "password"):
        assert col in msg


# ---------------------------------------------------------------------------
# BOM handling
# ---------------------------------------------------------------------------


def test_bom_handling(tmp_path: Path) -> None:
    """A UTF-8 BOM at the start of the file must not corrupt the header or values."""
    path = _csv_file(
        tmp_path,
        [{"name": "Site", "url": "https://example.com", "username": "user", "password": "pw", "note": ""}],
        bom=True,
    )
    result = import_csv(path)
    assert result.errors == []
    assert len(result.entries) == 1
    assert result.entries[0].title == "Site"


# ---------------------------------------------------------------------------
# Empty note → None
# ---------------------------------------------------------------------------


def test_empty_note_becomes_none(tmp_path: Path) -> None:
    """An empty note column must map to Entry.notes = None."""
    path = _csv_file(
        tmp_path,
        [{"name": "Site", "url": "https://example.com", "username": "u", "password": "pw", "note": ""}],
    )
    result = import_csv(path)
    assert result.entries[0].notes is None


def test_non_empty_note_is_preserved(tmp_path: Path) -> None:
    """A non-empty note must be stored verbatim in Entry.notes."""
    path = _csv_file(
        tmp_path,
        [{"name": "Site", "url": "https://example.com", "username": "u", "password": "pw", "note": "work"}],
    )
    result = import_csv(path)
    assert result.entries[0].notes == "work"


def test_note_column_absent_defaults_to_none(tmp_path: Path) -> None:
    """CSV without a note column at all must set Entry.notes = None."""
    path = tmp_path / "no_note.csv"
    path.write_text(
        "name,url,username,password\n"
        "Site,https://example.com,user,pw\n",
        encoding="utf-8",
    )
    result = import_csv(path)
    assert result.errors == []
    assert result.entries[0].notes is None


# ---------------------------------------------------------------------------
# Skipped rows (empty name / empty password)
# ---------------------------------------------------------------------------


def test_malformed_row_is_skipped(tmp_path: Path) -> None:
    """A row with an empty password must be skipped and reported, not abort import."""
    path = _csv_file(
        tmp_path,
        [
            {"name": "Good", "url": "https://good.com", "username": "user", "password": "goodpw", "note": ""},
            {"name": "Bad",  "url": "https://bad.com",  "username": "user", "password": "",        "note": ""},
        ],
    )
    result = import_csv(path)

    assert len(result.entries) == 1
    assert result.entries[0].title == "Good"
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err.row_number == 3  # header=1, Good=2, Bad=3
    assert "password" in err.reason


def test_empty_name_is_skipped(tmp_path: Path) -> None:
    """A row with an empty name must be skipped and reported."""
    path = _csv_file(
        tmp_path,
        [{"name": "", "url": "https://example.com", "username": "u", "password": "pw", "note": ""}],
    )
    result = import_csv(path)
    assert result.entries == []
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 2
    assert "name" in result.errors[0].reason


def test_multiple_skipped_rows_all_reported(tmp_path: Path) -> None:
    """Every bad row must appear in errors; good rows must still be returned."""
    path = _csv_file(
        tmp_path,
        [
            {"name": "A", "url": "", "username": "", "password": "pw1", "note": ""},
            {"name": "",  "url": "", "username": "", "password": "pw2", "note": ""},  # bad name
            {"name": "B", "url": "", "username": "", "password": "pw3", "note": ""},
            {"name": "C", "url": "", "username": "", "password": "",    "note": ""},  # bad password
        ],
    )
    result = import_csv(path)
    assert len(result.entries) == 2
    assert len(result.errors) == 2
    assert {e.row_number for e in result.errors} == {3, 5}


# ---------------------------------------------------------------------------
# Special characters in password
# ---------------------------------------------------------------------------


def test_special_characters_in_password(tmp_path: Path) -> None:
    """Passwords with commas, quotes, and Unicode must survive the CSV round-trip."""
    password = 'p@ss,w"ord—日本語'
    path = _csv_file(
        tmp_path,
        [{"name": "Site", "url": "https://example.com", "username": "user", "password": password, "note": ""}],
    )
    result = import_csv(path)
    assert result.errors == []
    assert result.entries[0].password == password


def test_special_characters_in_name_and_url(tmp_path: Path) -> None:
    """Titles and URLs with special characters must also survive unaltered."""
    title = 'Site "A" & B'
    path = _csv_file(
        tmp_path,
        [{"name": title, "url": "https://example.com/?q=a&b=1", "username": "u", "password": "pw", "note": ""}],
    )
    result = import_csv(path)
    assert result.entries[0].title == title
    assert result.entries[0].url == "https://example.com/?q=a&b=1"
