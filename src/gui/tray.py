"""System-tray icon: minimise-to-tray and restore/quit context menu."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow


class AppTray(QSystemTrayIcon):
    """Tray icon that keeps PassSimple accessible while the window is hidden.

    The context menu exposes two actions:
    - "Öffnen" — restore and focus the main window.
    - "Beenden" — trigger a clean application exit via MainWindow.quit_application().

    Double-clicking the tray icon also restores the window.
    """

    def __init__(self, parent: MainWindow, icon: QIcon) -> None:
        """Attach the tray icon to parent and build its context menu."""
        super().__init__(icon, parent)
        self.setToolTip("PassSimple")
        self._build_menu(parent)
        self.activated.connect(self._on_activated)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _build_menu(self, window: MainWindow) -> None:
        """Create and attach the right-click context menu."""
        menu = QMenu()
        open_action = menu.addAction("Öffnen")
        open_action.triggered.connect(lambda: _restore(window))
        menu.addSeparator()
        quit_action = menu.addAction("Beenden")
        quit_action.triggered.connect(window.quit_application)
        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Restore the main window when the user double-clicks the tray icon."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            _restore(self.parent())  # parent is always MainWindow


def _restore(window: object) -> None:
    """Bring window to the foreground, un-hiding it first if necessary."""
    w = window  # local alias; typed as object to avoid runtime MainWindow import
    getattr(w, "show")()
    getattr(w, "raise_")()
    getattr(w, "activateWindow")()
