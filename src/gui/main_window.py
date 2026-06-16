"""Main application window: sidebar (search + entry list) + detail pane."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Top-level window for PassSimple."""

    def __init__(self) -> None:
        """Initialise the main window layout."""
        super().__init__()
        raise NotImplementedError
