"""Frameless quick-search popup triggered by the global Ctrl+Alt+P hotkey."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.db import Vault
from src.gui.dialogs.entry_dialog import EntryDialog
from src.i18n import tr

# Single-instance clipboard timer shared across all popup invocations.
# Stored at module level so a new popup can cancel a previous popup's timer.
_clipboard_timer: QTimer | None = None


class QuickSearchPopup(QDialog):
    """Frameless quick-search popup for copying passwords without leaving the current app.

    Opens via the global Ctrl+Alt+P hotkey (registered in MainWindow).
    Supports live search, one-click password copy with 30 s clipboard auto-clear,
    and inline new-entry creation.
    """

    def __init__(self, vault: Vault, parent: QWidget | None = None) -> None:
        """Build the popup, centre it on the primary screen, and pre-load all entries."""
        super().__init__(parent)
        self._vault = vault

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(480, 400)
        self._init_ui()
        self._center_on_screen()
        # Show all entries (search_entries("") matches everything) on open.
        self._refresh_list("")

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Build the search field, results list, and action button row."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(tr("quicksearch.placeholder"))
        self._search_edit.textChanged.connect(self._refresh_list)
        # Enter in the search field copies the currently selected entry.
        self._search_edit.returnPressed.connect(self._on_copy_password)
        layout.addWidget(self._search_edit)

        self._list_widget = QListWidget()
        # Double-click or Enter on a list item copies the password.
        self._list_widget.itemDoubleClicked.connect(self._on_copy_password)
        self._list_widget.activated.connect(lambda _idx: self._on_copy_password())
        layout.addWidget(self._list_widget, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._copy_btn = QPushButton(tr("quicksearch.copy_password"))
        self._copy_btn.setObjectName("primary")
        self._copy_btn.setDefault(True)
        self._copy_btn.clicked.connect(self._on_copy_password)
        btn_row.addWidget(self._copy_btn)

        self._new_btn = QPushButton(tr("entry.button.new"))
        self._new_btn.clicked.connect(self._on_new_entry)
        btn_row.addWidget(self._new_btn)

        layout.addLayout(btn_row)

    # -----------------------------------------------------------------------
    # Live retranslation
    # -----------------------------------------------------------------------

    def retranslate(self) -> None:
        """Update all visible strings after a language change."""
        self._search_edit.setPlaceholderText(tr("quicksearch.placeholder"))
        self._copy_btn.setText(tr("quicksearch.copy_password"))
        self._new_btn.setText(tr("entry.button.new"))

    # -----------------------------------------------------------------------
    # Qt event overrides
    # -----------------------------------------------------------------------

    def showEvent(self, event: object) -> None:
        """Focus the search field every time the popup becomes visible."""
        super().showEvent(event)  # type: ignore[arg-type]
        self._search_edit.setFocus()
        self._search_edit.selectAll()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard shortcuts for closing the popup.

        Esc: clears the search field if it has text (first press), or closes
             the popup if the field is already empty (second press).
        Ctrl+W: closes immediately (Windows convention).
        """
        if event.key() == Qt.Key.Key_Escape:
            if self._search_edit.text():
                self._search_edit.clear()
            else:
                self.close()
        elif event.key() == Qt.Key.Key_W and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.close()
        else:
            super().keyPressEvent(event)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _center_on_screen(self) -> None:
        """Move the popup to the centre of the primary screen."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geom = screen.availableGeometry()
        self.move(
            geom.center().x() - self.width() // 2,
            geom.center().y() - self.height() // 2,
        )

    def _refresh_list(self, text: str) -> None:
        """Repopulate the results list from a live vault search.

        Empty text returns all entries sorted by most-recently modified.
        """
        try:
            entries = self._vault.search_entries(text, sort="updated_desc")
        except Exception:
            return

        self._list_widget.clear()
        for entry in entries:
            label = entry.title
            if entry.username:
                label = f"{entry.title} — {entry.username}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self._list_widget.addItem(item)

        if self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)

    # -----------------------------------------------------------------------
    # Action handlers
    # -----------------------------------------------------------------------

    def _on_copy_password(self) -> None:
        """Copy the selected entry's password to the clipboard, then close.

        Starts a 30-second auto-clear timer (module-level so a new popup
        invocation cancels any previous timer before starting a fresh one).
        """
        global _clipboard_timer

        item = self._list_widget.currentItem()
        if item is None:
            return

        entry_id: int = item.data(Qt.ItemDataRole.UserRole)
        try:
            entry = self._vault.get_entry(entry_id)
        except Exception:
            return
        if entry is None or not entry.password:
            return

        QApplication.clipboard().setText(entry.password)

        # Cancel any running timer before starting the new 30 s countdown.
        if _clipboard_timer is not None:
            _clipboard_timer.stop()

        # Parent the timer to QApplication so it survives this dialog's close.
        _clipboard_timer = QTimer(QApplication.instance())
        _clipboard_timer.setSingleShot(True)
        _clipboard_timer.timeout.connect(QApplication.clipboard().clear)
        _clipboard_timer.start(30_000)

        self.accept()

    def _on_new_entry(self) -> None:
        """Open EntryDialog; on accept persist to vault and close the popup."""
        dlg = EntryDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_entry()
        try:
            self._vault.add_entry(
                data.title,
                data.password or "",
                username=data.username or None,
                url=data.url or None,
                notes=data.notes or None,
                tag_names=[t.name for t in data.tags] if data.tags else None,
            )
        except Exception:
            return
        self.close()
