"""Shared GUI utility functions."""

from __future__ import annotations

import subprocess


def plural_entries(count: int) -> str:
    """Return '1 Eintrag' or 'N Einträge'."""
    return f"{count} Eintrag" if count == 1 else f"{count} Einträge"


def get_git_short_hash() -> str:
    """Return the current git short commit hash, or 'unbekannt' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unbekannt"
