"""Application settings dialog (theme toggle, etc.)."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog


class SettingsDialog(QDialog):
    """Modal dialog for app-wide settings."""

    def __init__(self, parent=None) -> None:
        """Initialise the settings dialog."""
        super().__init__(parent)
        raise NotImplementedError
