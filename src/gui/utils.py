"""Shared GUI utility functions."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone


def plural_entries(count: int) -> str:
    """Return '1 Eintrag' or 'N Einträge'."""
    return f"{count} Eintrag" if count == 1 else f"{count} Einträge"


def relative_time(iso_timestamp: str) -> str:
    """Convert an ISO 8601 timestamp to a German relative-time string.

    Returns strings like 'vor 3 Minuten', 'vor 1 Tag', 'vor 2 Jahren'.
    Returns an empty string if the timestamp cannot be parsed.
    """
    try:
        ts = datetime.fromisoformat(iso_timestamp)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return ""

    delta = datetime.now(timezone.utc) - ts
    seconds = max(0, int(delta.total_seconds()))

    if seconds < 60:
        n = seconds
        return f"vor {n} Sekunde" if n == 1 else f"vor {n} Sekunden"
    minutes = seconds // 60
    if minutes < 60:
        return f"vor {minutes} Minute" if minutes == 1 else f"vor {minutes} Minuten"
    hours = minutes // 60
    if hours < 24:
        return f"vor {hours} Stunde" if hours == 1 else f"vor {hours} Stunden"
    days = hours // 24
    if days < 30:
        return f"vor {days} Tag" if days == 1 else f"vor {days} Tagen"
    months = days // 30
    if months < 12:
        return f"vor {months} Monat" if months == 1 else f"vor {months} Monaten"
    years = days // 365
    return f"vor {years} Jahr" if years == 1 else f"vor {years} Jahren"


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
