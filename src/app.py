"""Entry point for PassSimple."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src import crypto
from src.db import Vault, _DDL
from src.gui.main_window import MainWindow

_ASSETS_DIR = Path(__file__).parent.parent / "assets"

# Row key under which the DPAPI-protected master key blob is stored in vault_meta.
_META_KEY = "dpapi_master_key"


def _bootstrap_master_key(db_path: Path) -> bytes:
    """Ensure the vault schema exists and return the plaintext master key.

    First launch: generates a fresh 32-byte master key, encrypts it with DPAPI
    (user-scope, no passphrase), persists the blob, and returns the plaintext key.

    Subsequent launches: reads the stored DPAPI blob and decrypts it.

    The connection opened here is intentionally short-lived and closed before
    Vault.open() is called, which opens its own connection with the full
    runtime configuration (row_factory, foreign_keys pragma).

    Raises any exception from DPAPI to the caller — pywintypes.error is the
    typical signal that the blob was sealed by a different Windows account.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        # executescript is idempotent: every statement uses IF NOT EXISTS.
        conn.executescript(_DDL)

        row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = ?", (_META_KEY,)
        ).fetchone()

        if row is None:
            # First launch: create and protect the master key.
            #
            # Why no passphrase?  DPAPI binds the ciphertext to the Windows user
            # account itself (hardware TPM or DPAPI service key derived from the
            # login credentials).  Adding a separate passphrase would only help if
            # an attacker obtained the raw vault file without OS access — but at
            # that point, Windows credential isolation already prevents DPAPI from
            # decrypting.  A passphrase would shift the burden to the user without
            # meaningful security gain on a single-user desktop.
            master_key = crypto.generate_master_key()
            dpapi_blob = crypto.protect_master_key(master_key)
            conn.execute(
                "INSERT INTO vault_meta (key, value) VALUES (?, ?)",
                (_META_KEY, dpapi_blob),
            )
            conn.commit()
            return master_key

        # Subsequent launch: decrypt the stored blob.
        #
        # Why keep the plaintext key in RAM?  Python strings and bytes objects are
        # immutable; there is no reliable way to zero them out before GC.  The key
        # lives only in Vault._master_key while the app runs, and is cleared by
        # Vault.close() on exit.  Minimising lifetime is the best we can do.
        return crypto.unprotect_master_key(bytes(row[0]))
    finally:
        conn.close()


def main() -> int:
    """Bootstrap the vault and start the Qt event loop. Returns the exit code."""
    app = QApplication(sys.argv)
    app.setApplicationName("PassSimple")
    app.setOrganizationName("PassSimple")

    icon_path = _ASSETS_DIR / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    db_path = Vault.default_path()

    try:
        master_key = _bootstrap_master_key(db_path)
    except Exception:
        # pywintypes.error is raised when DPAPI cannot decrypt — most commonly
        # because the vault was created under a different Windows account.
        # The key is then unrecoverable by design: DPAPI user-scope binding
        # means that without the original account, the data is permanently sealed.
        QMessageBox.critical(
            None,
            "Fehler",
            "Vault konnte nicht entschlüsselt werden.\n"
            "Möglicherweise wurde er von einem anderen Benutzerkonto erstellt.",
        )
        return 1

    vault = Vault()
    try:
        vault.open(master_key, path=db_path)
    except Exception as e:
        QMessageBox.critical(None, "Fehler", str(e))
        return 1

    window = MainWindow(vault, master_key)
    window.show()

    exit_code = app.exec()
    vault.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
