"""Dialog for creating and editing vault entries."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog

from src.models import Entry


class EntryDialog(QDialog):
    """Modal dialog for add / edit entry."""

    def __init__(self, entry: Entry | None = None, parent=None) -> None:
        """Open in create mode when entry is None, edit mode otherwise."""
        super().__init__(parent)
        raise NotImplementedError

    def get_entry(self) -> Entry:
        """Return the entry as filled in by the user."""
        raise NotImplementedError
