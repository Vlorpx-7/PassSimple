"""Shared GUI utility functions."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone


def plural_entries(count: int) -> str:
    """Return a localised count+noun string, e.g. '1 Eintrag' / '1 entry'."""
    from src.i18n import tr
    word = tr("entry.singular") if count == 1 else tr("entry.plural")
    return f"{count} {word}"


def _time_key(unit: str, n: int) -> str:
    from src.i18n import tr
    suffix = "one" if n == 1 else "other"
    return tr(f"time.{unit}_ago_{suffix}").format(n=n)


def relative_time(iso_timestamp: str) -> str:
    """Convert an ISO 8601 timestamp to a localised relative-time string.

    Returns strings like '3 minutes ago' / 'vor 3 Minuten', 'just now', etc.
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
        return _time_key("seconds", seconds)
    n = seconds // 60
    if n < 60:
        return _time_key("minutes", n)
    n = n // 60
    if n < 24:
        return _time_key("hours", n)
    n = n // 24
    if n < 30:
        return _time_key("days", n)
    n = n // 30
    if n < 12:
        return _time_key("months", n)
    n = seconds // (365 * 24 * 3600)
    return _time_key("years", n)


def get_git_short_hash() -> str:
    """Return the short commit hash for the running build.

    Resolution order:
      1. src._build_info.COMMIT_HASH — injected by build.ps1 at bundle time.
      2. subprocess git rev-parse   — works in a dev checkout with git present.
      3. 'unbekannt'                — fallback when neither source is available.
    """
    from src._build_info import COMMIT_HASH

    if COMMIT_HASH != "dev":
        return COMMIT_HASH
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


def get_build_date() -> str:
    """Return the build date as 'YYYY-MM-DD'.

    Resolution order:
      1. src._build_info.BUILD_DATE — injected by build.ps1 at bundle time.
      2. datetime.now()             — current date in dev mode.
    """
    from src._build_info import BUILD_DATE

    if BUILD_DATE:
        return BUILD_DATE
    return datetime.now(timezone.utc).date().isoformat()
