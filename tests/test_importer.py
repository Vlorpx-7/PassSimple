"""Tests for src/importer.py — Chromium CSV parsing."""

from pathlib import Path

import pytest

from src.importer import ImportError, parse_csv


def test_valid_csv(tmp_path: Path) -> None:
    """A well-formed Chromium CSV should parse without errors."""
    raise NotImplementedError


def test_missing_required_columns(tmp_path: Path) -> None:
    """CSV without required columns must raise ImportError."""
    raise NotImplementedError


def test_bom_handling(tmp_path: Path) -> None:
    """CSV with UTF-8 BOM should parse correctly."""
    raise NotImplementedError


def test_empty_note_becomes_none(tmp_path: Path) -> None:
    """Empty note column should map to None in the Entry."""
    raise NotImplementedError


def test_malformed_row_is_skipped(tmp_path: Path) -> None:
    """A malformed row should be skipped and reported, not abort the import."""
    raise NotImplementedError


def test_special_characters_in_password(tmp_path: Path) -> None:
    """Passwords containing commas, quotes, and Unicode must survive the round-trip."""
    raise NotImplementedError
