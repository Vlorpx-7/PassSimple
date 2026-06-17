"""SQLite connection factory: configures row_factory and foreign_keys pragma."""

import sqlite3
from pathlib import Path


def open_connection(path: Path) -> sqlite3.Connection:
    """Open a SQLite connection to path with row_factory and foreign_keys enabled."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    # Foreign key enforcement is OFF by default in SQLite — must be set per connection.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
