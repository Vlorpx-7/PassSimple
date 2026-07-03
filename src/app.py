"""Entry point for PassSimple."""

from __future__ import annotations

import sqlite3
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.bootstrap import initialize_vault_schema_if_needed, load_or_create_master_key
from src.db import Vault
from src.gui.main_window import MainWindow
from src.gui.splash import create_splash
from src.gui.title_bar import set_current_theme
from src.i18n import Translator, tr
from src.paths import resource_path


def main() -> int:
    """Bootstrap the vault and start the Qt event loop. Returns the exit code."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("PassSimple")
    app.setApplicationDisplayName("")
    app.setOrganizationName("PassSimple")

    icon_path = resource_path("assets/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    db_path = Vault.default_path()

    # Read the persisted language before showing the splash so the splash text
    # renders in the correct language on first paint.
    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = 'language'"
        ).fetchone()
        conn.close()
        if row:
            lang = row[0].decode() if isinstance(row[0], bytes) else str(row[0])
            Translator.instance().set_language(lang)
    except Exception:
        pass  # DB may not exist yet (first run); Translator defaults to "de"

    # Show splash before any vault work so the user sees something immediately.
    splash = create_splash()
    splash.show()
    app.processEvents()

    try:
        initialize_vault_schema_if_needed(db_path)
        master_key = load_or_create_master_key(db_path)
    except Exception:
        # pywintypes.error is raised when DPAPI cannot decrypt — most commonly
        # because the vault was created under a different Windows account.
        # The key is then unrecoverable by design: DPAPI user-scope binding
        # means that without the original account, the data is permanently sealed.
        splash.close()
        QMessageBox.critical(None, tr("error.title"), tr("error.vault_decrypt"))
        return 1

    vault = Vault()
    try:
        vault.open(master_key, path=db_path)
    except Exception as e:
        splash.close()
        QMessageBox.critical(None, tr("error.title"), str(e))
        return 1

    # Seed the title-bar theme cache before any window or dialog is created.
    theme_bytes = vault.get_meta("theme")
    set_current_theme("light" if theme_bytes == b"light" else "dark")

    window = MainWindow(vault, master_key)

    # 800 ms minimum display time prevents the splash from flickering away
    # instantly when the vault is already decrypted (fast path).
    # splash.finish(window) defers the close until the main window is fully painted.
    QTimer.singleShot(800, lambda: (splash.finish(window), window.show()))

    exit_code = app.exec()
    vault.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
