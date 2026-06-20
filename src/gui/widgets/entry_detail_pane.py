"""Right pane: entry detail view with password controls, star toggle, and CRUD actions."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.models import Entry

_ASSETS_DIR = Path(__file__).parent.parent.parent.parent / "assets"


class EntryDetailPane(QWidget):
    """Read-only detail view for the currently selected vault entry.

    Emits signals for all mutating actions so the main window can handle vault
    interaction and error display.

    Signals
    -------
    new_entry_requested()
        User clicked "+ Neuer Eintrag".
    edit_entry_requested(int)
        User clicked "Bearbeiten"; carries the current entry id.
    delete_entry_requested(int)
        User clicked "Loeschen"; carries the current entry id.
    favorite_toggled(int, bool)
        User clicked the star button; carries (entry_id, new_state).
    status_message(str)
        Short text for the main window's status bar (clipboard events).
    """

    new_entry_requested = Signal()
    edit_entry_requested = Signal(int)
    delete_entry_requested = Signal(int)
    favorite_toggled = Signal(int, bool)
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the detail pane in the empty/disabled state."""
        super().__init__(parent)
        self._current_entry_id: int | None = None
        # Stored as instance variable with self as Qt parent to survive until fired.
        self._clipboard_timer: QTimer | None = None
        self._init_ui()
        self.clear()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Lay out the toolbar, then a stacked widget (empty-state / form)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addLayout(self._build_toolbar())

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # Index 0 — empty state (no entry selected)
        self._stack.addWidget(self._build_empty_state())

        # Index 1 — entry form + action buttons
        form_container = QWidget()
        form_vl = QVBoxLayout(form_container)
        form_vl.setContentsMargins(0, 0, 0, 0)
        form_vl.setSpacing(10)
        form_vl.addLayout(self._build_form())
        form_vl.addLayout(self._build_action_row())
        form_vl.addStretch()
        self._stack.addWidget(form_container)

    def _build_toolbar(self) -> QHBoxLayout:
        """Top toolbar: stretch on the left, '+ Neuer Eintrag' on the right."""
        row = QHBoxLayout()
        row.addStretch()
        new_btn = QPushButton("+ Neuer Eintrag")
        new_btn.setObjectName("primary")
        new_btn.setToolTip("Neuen Eintrag erstellen (Strg+N)")
        new_btn.clicked.connect(self.new_entry_requested.emit)
        row.addWidget(new_btn)
        return row

    def _build_empty_state(self) -> QWidget:
        """Centered placeholder shown when no entry is selected."""
        widget = QWidget()
        vl = QVBoxLayout(widget)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.setSpacing(12)

        icon_lbl = QLabel()
        icon_path = _ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            pixmap = QIcon(str(icon_path)).pixmap(QSize(96, 96))
            icon_lbl.setPixmap(pixmap)
            effect = QGraphicsOpacityEffect(icon_lbl)
            effect.setOpacity(0.30)
            icon_lbl.setGraphicsEffect(effect)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(icon_lbl)

        main_lbl = QLabel("Wähle einen Eintrag aus der Liste")
        main_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(13)
        main_lbl.setFont(font)
        vl.addWidget(main_lbl)

        sub_lbl = QLabel("oder erstelle einen neuen mit + Neuer Eintrag")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(sub_lbl)

        return widget

    def _build_form(self) -> QFormLayout:
        """Form with all entry fields. Password row includes eye and copy buttons."""
        form = QFormLayout()
        form.setSpacing(8)

        # Title + star toggle in a single row.
        title_row = QWidget()
        title_hl = QHBoxLayout(title_row)
        title_hl.setContentsMargins(0, 0, 0, 0)
        title_hl.setSpacing(4)

        self._title_edit = QLineEdit()
        self._title_edit.setReadOnly(True)
        title_hl.addWidget(self._title_edit, 1)

        self._star_btn = QPushButton("☆")
        self._star_btn.setObjectName("starToggle")
        self._star_btn.setCheckable(True)
        self._star_btn.setFixedWidth(36)
        self._star_btn.setToolTip("Als Favorit markieren")
        # Use clicked(checked) so setChecked() in load_entry() doesn't emit.
        self._star_btn.clicked.connect(self._on_star_clicked)
        title_hl.addWidget(self._star_btn)

        form.addRow("Titel:", title_row)

        self._url_edit = QLineEdit()
        self._url_edit.setReadOnly(True)
        form.addRow("URL:", self._url_edit)

        self._username_edit = QLineEdit()
        self._username_edit.setReadOnly(True)
        form.addRow("Username:", self._username_edit)

        form.addRow("Passwort:", self._build_password_row())

        self._notes_edit = QTextEdit()
        self._notes_edit.setReadOnly(True)
        self._notes_edit.setMaximumHeight(100)
        form.addRow("Notizen:", self._notes_edit)

        self._tags_label = QLabel()
        self._tags_label.setWordWrap(True)
        form.addRow("Tags:", self._tags_label)

        return form

    def _build_password_row(self) -> QWidget:
        """Password field with eye-toggle and copy-to-clipboard button."""
        widget = QWidget()
        hl = QHBoxLayout(widget)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)

        self._password_edit = QLineEdit()
        self._password_edit.setReadOnly(True)
        self._password_edit.setEchoMode(QLineEdit.Password)
        hl.addWidget(self._password_edit, 1)

        self._eye_btn = QPushButton("Anzeigen")
        self._eye_btn.setCheckable(True)
        self._eye_btn.setFixedWidth(80)
        self._eye_btn.setToolTip("Passwort anzeigen / verbergen")
        self._eye_btn.toggled.connect(self._on_eye_toggled)
        hl.addWidget(self._eye_btn)

        self._copy_btn = QPushButton("Kopieren")
        self._copy_btn.setFixedWidth(80)
        self._copy_btn.setToolTip("Passwort in Zwischenablage (30 s automatisches Löschen)")
        self._copy_btn.clicked.connect(self._on_copy_password)
        hl.addWidget(self._copy_btn)

        return widget

    def _build_action_row(self) -> QHBoxLayout:
        """Bearbeiten and Loeschen buttons, left-aligned."""
        row = QHBoxLayout()
        self._edit_btn = QPushButton("Bearbeiten")
        self._edit_btn.setToolTip("Eintrag bearbeiten")
        self._edit_btn.clicked.connect(self._on_edit)
        self._delete_btn = QPushButton("Loeschen")
        self._delete_btn.setObjectName("danger")
        self._delete_btn.setToolTip("Eintrag löschen")
        self._delete_btn.clicked.connect(self._on_delete)
        row.addWidget(self._edit_btn)
        row.addWidget(self._delete_btn)
        row.addStretch()
        return row

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def load_entry(self, entry: Entry) -> None:
        """Populate all fields from entry and enable action controls."""
        self._current_entry_id = entry.id

        self._title_edit.setText(entry.title)
        self._url_edit.setText(entry.url or "")
        self._username_edit.setText(entry.username or "")
        self._password_edit.setText(entry.password or "")
        self._notes_edit.setPlainText(entry.notes or "")
        self._tags_label.setText(", ".join(t.name for t in entry.tags))

        # Reset the eye toggle without emitting signals.
        self._eye_btn.blockSignals(True)
        self._eye_btn.setChecked(False)
        self._eye_btn.setText("Anzeigen")
        self._eye_btn.blockSignals(False)
        self._password_edit.setEchoMode(QLineEdit.Password)

        # Set star state without emitting clicked/favorite_toggled.
        self._star_btn.setChecked(entry.is_favorite)
        self._star_btn.setText("★" if entry.is_favorite else "☆")

        self._set_entry_controls_enabled(True)
        self._stack.setCurrentIndex(1)

    def clear(self) -> None:
        """Clear all fields and disable action controls."""
        self._current_entry_id = None

        self._title_edit.clear()
        self._url_edit.clear()
        self._username_edit.clear()
        self._password_edit.clear()
        self._notes_edit.clear()
        self._tags_label.clear()

        self._star_btn.setChecked(False)
        self._star_btn.setText("☆")

        self._eye_btn.blockSignals(True)
        self._eye_btn.setChecked(False)
        self._eye_btn.setText("Anzeigen")
        self._eye_btn.blockSignals(False)
        self._password_edit.setEchoMode(QLineEdit.Password)

        self._set_entry_controls_enabled(False)
        self._stack.setCurrentIndex(0)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _set_entry_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable controls that require a loaded entry."""
        for widget in (
            self._edit_btn,
            self._delete_btn,
            self._star_btn,
            self._eye_btn,
            self._copy_btn,
        ):
            widget.setEnabled(enabled)

    # -----------------------------------------------------------------------
    # Signal handlers — password controls
    # -----------------------------------------------------------------------

    def _on_eye_toggled(self, checked: bool) -> None:
        """Toggle the password field between masked and plaintext mode."""
        if checked:
            self._password_edit.setEchoMode(QLineEdit.Normal)
            self._eye_btn.setText("Verbergen")
        else:
            self._password_edit.setEchoMode(QLineEdit.Password)
            self._eye_btn.setText("Anzeigen")

    def _on_copy_password(self) -> None:
        """Copy the password to the clipboard; auto-clear after 30 seconds.

        The QTimer is stored as self._clipboard_timer with self as Qt parent so
        it survives until it fires.  A new copy cancels any running timer.
        """
        text = self._password_edit.text()
        if not text:
            return

        QApplication.clipboard().setText(text)
        self.status_message.emit("In Zwischenablage kopiert — wird in 30 s gelöscht")

        if self._clipboard_timer is not None:
            self._clipboard_timer.stop()

        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.setSingleShot(True)
        self._clipboard_timer.timeout.connect(self._clear_clipboard)
        self._clipboard_timer.start(30_000)

    def _clear_clipboard(self) -> None:
        """Clear the clipboard after the 30-second timeout."""
        QApplication.clipboard().clear()
        self.status_message.emit("Zwischenablage gelöscht")
        self._clipboard_timer = None

    # -----------------------------------------------------------------------
    # Signal handlers — star toggle
    # -----------------------------------------------------------------------

    def _on_star_clicked(self, checked: bool) -> None:
        """Update button text and emit favorite_toggled.

        Connected to clicked(checked) — fires only on user interaction, not on
        programmatic setChecked() calls, so load_entry() won't trigger vault writes.
        """
        self._star_btn.setText("★" if checked else "☆")
        if self._current_entry_id is not None:
            self.favorite_toggled.emit(self._current_entry_id, checked)

    # -----------------------------------------------------------------------
    # Signal handlers — CRUD actions
    # -----------------------------------------------------------------------

    def _on_edit(self) -> None:
        """Emit edit_entry_requested if an entry is loaded."""
        if self._current_entry_id is not None:
            self.edit_entry_requested.emit(self._current_entry_id)

    def _on_delete(self) -> None:
        """Emit delete_entry_requested if an entry is loaded."""
        if self._current_entry_id is not None:
            self.delete_entry_requested.emit(self._current_entry_id)
