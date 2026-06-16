"""CSV importer for Chromium-based browsers (Chrome, Edge, Brave).

All three browsers export the same format, so one parser handles all of them.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from src.models import Entry

_REQUIRED_COLUMNS: frozenset[str] = frozenset({"name", "url", "username", "password"})


@dataclass
class ImportError:  # intentionally shadows the builtin within this module
    """Describes a single row that could not be imported."""

    row_number: int
    reason: str


@dataclass
class ImportResult:
    """Outcome of an import run: successfully parsed entries and per-row errors."""

    entries: list[Entry] = field(default_factory=list)
    errors: list[ImportError] = field(default_factory=list)


def import_csv(path: Path) -> ImportResult:
    """Parse a Chromium password-export CSV and return entries + per-row errors.

    Expected columns (Edge / Chrome / Brave all use this format)::

        name, url, username, password, note

    Column mapping:
        name     → Entry.title
        note     → Entry.notes  (empty string → None)
        url, username, password → 1-to-1

    Raises ValueError if any required column (name, url, username, password) is absent.

    Per-row rules:
        - empty name     → skip row, record ImportError
        - empty password → skip row, record ImportError
        - empty note     → Entry.notes = None
        - other fields stay as-is (empty string remains empty string)

    The returned Entry objects carry the plaintext password in Entry.password and
    password_ct=b"" — callers must pass them to Vault.add_entry() to encrypt.
    """
    entries: list[Entry] = []
    errors: list[ImportError] = []

    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)

        # Accessing .fieldnames triggers reading of the header row.
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header row")

        missing = _REQUIRED_COLUMNS - frozenset(reader.fieldnames)
        if missing:
            raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")

        # Data rows start at line 2 (line 1 is the header).
        for row_num, row in enumerate(reader, start=2):
            name = row.get("name") or ""
            password = row.get("password") or ""

            if not name:
                errors.append(ImportError(row_number=row_num, reason="empty name"))
                continue

            if not password:
                errors.append(ImportError(row_number=row_num, reason="empty password"))
                continue

            # Only note gets the empty-string → None treatment; other fields stay as-is.
            note_raw = row.get("note")
            notes: str | None = note_raw if note_raw else None

            entries.append(
                Entry(
                    id=None,
                    title=name,
                    username=row.get("username", ""),
                    password_ct=b"",   # placeholder — caller must encrypt via Vault
                    url=row.get("url", ""),
                    notes=notes,
                    created_at="",     # set by Vault.add_entry at import time
                    updated_at="",
                    password=password, # plaintext, held only until Vault.add_entry is called
                )
            )

    return ImportResult(entries=entries, errors=errors)
