"""Bootstrap: vault schema initialisation and DPAPI master key management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src import crypto
from src.db.schema import _DDL

# Row key under which the DPAPI-protected master key blob is stored in vault_meta.
_META_KEY = "dpapi_master_key"


def initialize_vault_schema_if_needed(path: Path) -> None:
    """Ensure the vault directory exists and the SQLite schema is initialised.

    Safe to call on every launch — all DDL statements use IF NOT EXISTS.
    Uses a short-lived raw connection that is closed before Vault.open() runs.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        # executescript issues an implicit COMMIT before running — that's fine here.
        conn.executescript(_DDL)
    finally:
        conn.close()


def load_or_create_master_key(path: Path) -> bytes:
    """Return the plaintext master key, creating and persisting one on first launch.

    First launch: generates a fresh 32-byte master key, encrypts it with DPAPI
    (user-scope, no passphrase), persists the blob, and returns the plaintext key.

    Subsequent launches: reads the stored DPAPI blob and decrypts it.

    Why no passphrase?  DPAPI binds the ciphertext to the Windows user account
    itself (hardware TPM or DPAPI service key derived from login credentials).
    Adding a separate passphrase would only help if an attacker obtained the raw
    vault file without OS access — but at that point, Windows credential isolation
    already prevents DPAPI from decrypting.  A passphrase would shift the burden
    to the user without meaningful security gain on a single-user desktop.

    Why keep the plaintext key in RAM?  Python strings and bytes objects are
    immutable; there is no reliable way to zero them out before GC.  The key lives
    only in Vault._master_key while the app runs and is cleared by Vault.close().
    Minimising lifetime is the best we can do.

    Raises pywintypes.error when DPAPI cannot decrypt — most commonly because
    the vault was sealed by a different Windows account.
    """
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = ?", (_META_KEY,)
        ).fetchone()

        if row is None:
            master_key = crypto.generate_master_key()
            dpapi_blob = crypto.protect_master_key(master_key)
            conn.execute(
                "INSERT INTO vault_meta (key, value) VALUES (?, ?)",
                (_META_KEY, dpapi_blob),
            )
            conn.commit()
            return master_key

        return crypto.unprotect_master_key(bytes(row[0]))
    finally:
        conn.close()
