"""CSV importer for Chromium-based browsers (Chrome, Edge, Brave)."""

from __future__ import annotations

from pathlib import Path

from src.models import Entry


class ImportError(Exception):
    """Raised when the CSV file cannot be parsed at all."""


def parse_csv(path: Path) -> tuple[list[Entry], list[tuple[int, str]]]:
    """Parse a Chromium password export CSV.

    Returns a tuple of (valid_entries, errors) where errors is a list of
    (row_number, error_message) pairs for rows that could not be parsed.
    """
    raise NotImplementedError
