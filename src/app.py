"""Entry point for PassSimple."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.bootstrap import initialize_vault_schema_if_needed, load_or_create_master_key
from src.db import Vault
from src.gui.main_window import MainWindow
from src.gui.splash import create_splash
from src.gui.title_bar import set_current_theme

_ASSETS_DIR = Path(__file__).parent.parent / "assets"


def main() -> int:
    """Bootstrap the vault and start the Qt event loop. Returns the exit code."""
    app = QApplication(sys.argv)
    app.setApplicationName("PassSimple")
    app.setApplicationDisplayName("")
    app.setOrganizationName("PassSimple")

    icon_path = _ASSETS_DIR / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Show splash before any vault work so the user sees something immediately.
    splash = create_splash()
    splash.show()
    app.processEvents()

    db_path = Vault.default_path()

    try:
        initialize_vault_schema_if_needed(db_path)
        master_key = load_or_create_master_key(db_path)
    except Exception:
        # pywintypes.error is raised when DPAPI cannot decrypt — most commonly
        # because the vault was created under a different Windows account.
        # The key is then unrecoverable by design: DPAPI user-scope binding
        # means that without the original account, the data is permanently sealed.
        splash.close()
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
        splash.close()
        QMessageBox.critical(None, "Fehler", str(e))
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
