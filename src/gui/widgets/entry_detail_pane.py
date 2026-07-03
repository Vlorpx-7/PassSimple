"""Right pane: entry detail view with password controls, star toggle, and CRUD actions."""

from __future__ import annotations

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

from src.i18n import tr
from src.models import Entry
from src.paths import resource_path


class EntryDetailPane(QWidget):
    """Read-only detail view for the currently selected vault entry.

    Emits signals for all mutating actions so the main window can handle vault
    interaction and error display.

    Signals
    -------
    new_entry_requested()
        User clicked "+ New Entry".
    edit_entry_requested(int)
        User clicked "Edit"; carries the current entry id.
    delete_entry_requested(int)
        User clicked "Delete"; carries the current entry id.
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
        """Top toolbar: stretch on the left, '+ New Entry' on the right."""
        row = QHBoxLayout()
        row.addStretch()
        self._new_btn = QPushButton(tr("entry.button.new"))
        self._new_btn.setObjectName("primary")
        self._new_btn.setToolTip(tr("entry.button.new_tooltip"))
        self._new_btn.clicked.connect(self.new_entry_requested.emit)
        row.addWidget(self._new_btn)
        return row

    def _build_empty_state(self) -> QWidget:
        """Centered placeholder shown when no entry is selected."""
        widget = QWidget()
        vl = QVBoxLayout(widget)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.setSpacing(12)

        icon_lbl = QLabel()
        icon_path = resource_path("assets/icon.ico")
        if icon_path.exists():
            pixmap = QIcon(str(icon_path)).pixmap(QSize(96, 96))
            icon_lbl.setPixmap(pixmap)
            effect = QGraphicsOpacityEffect(icon_lbl)
            effect.setOpacity(0.30)
            icon_lbl.setGraphicsEffect(effect)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(icon_lbl)

        self._empty_select_lbl = QLabel(tr("entry.empty.select"))
        self._empty_select_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(13)
        self._empty_select_lbl.setFont(font)
        vl.addWidget(self._empty_select_lbl)

        self._empty_hint_lbl = QLabel(tr("entry.empty.hint"))
        self._empty_hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(self._empty_hint_lbl)

        return widget

    def _build_form(self) -> QFormLayout:
        """Form with all entry fields. Password row includes eye and copy buttons."""
        self._form = QFormLayout()
        self._form.setSpacing(8)

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
        self._star_btn.setToolTip(tr("entry.button.favorite_tooltip"))
        # Use clicked(checked) so setChecked() in load_entry() doesn't emit.
        self._star_btn.clicked.connect(self._on_star_clicked)
        title_hl.addWidget(self._star_btn)

        self._form.addRow(tr("entry.field.title") + ":", title_row)

        self._url_edit = QLineEdit()
        self._url_edit.setReadOnly(True)
        self._form.addRow(tr("entry.field.url") + ":", self._url_edit)

        self._username_edit = QLineEdit()
        self._username_edit.setReadOnly(True)
        self._form.addRow(tr("entry.field.username") + ":", self._username_edit)

        self._form.addRow(tr("entry.field.password") + ":", self._build_password_row())

        self._notes_edit = QTextEdit()
        self._notes_edit.setReadOnly(True)
        self._notes_edit.setMaximumHeight(100)
        self._form.addRow(tr("entry.field.notes") + ":", self._notes_edit)

        self._tags_label = QLabel()
        self._tags_label.setWordWrap(True)
        self._form.addRow(tr("entry.field.tags") + ":", self._tags_label)

        return self._form

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

        self._eye_btn = QPushButton(tr("entry.button.show"))
        self._eye_btn.setCheckable(True)
        self._eye_btn.setFixedWidth(80)
        self._eye_btn.setToolTip(tr("entry.button.show_hide_tooltip"))
        self._eye_btn.toggled.connect(self._on_eye_toggled)
        hl.addWidget(self._eye_btn)

        self._copy_btn = QPushButton(tr("entry.button.copy"))
        self._copy_btn.setFixedWidth(80)
        self._copy_btn.setToolTip(tr("entry.button.copy_tooltip"))
        self._copy_btn.clicked.connect(self._on_copy_password)
        hl.addWidget(self._copy_btn)

        return widget

    def _build_action_row(self) -> QHBoxLayout:
        """Edit and Delete buttons, left-aligned."""
        row = QHBoxLayout()
        self._edit_btn = QPushButton(tr("entry.button.edit"))
        self._edit_btn.setToolTip(tr("entry.button.edit_tooltip"))
        self._edit_btn.clicked.connect(self._on_edit)
        self._delete_btn = QPushButton(tr("entry.button.delete"))
        self._delete_btn.setObjectName("danger")
        self._delete_btn.setToolTip(tr("entry.button.delete_tooltip"))
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
        self._eye_btn.setText(tr("entry.button.show"))
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
        self._eye_btn.setText(tr("entry.button.show"))
        self._eye_btn.blockSignals(False)
        self._password_edit.setEchoMode(QLineEdit.Password)

        self._set_entry_controls_enabled(False)
        self._stack.setCurrentIndex(0)

    # -----------------------------------------------------------------------
    # Live retranslation
    # -----------------------------------------------------------------------

    def retranslate(self) -> None:
        """Update all visible strings after a language change."""
        self._new_btn.setText(tr("entry.button.new"))
        self._new_btn.setToolTip(tr("entry.button.new_tooltip"))

        self._empty_select_lbl.setText(tr("entry.empty.select"))
        self._empty_hint_lbl.setText(tr("entry.empty.hint"))

        # Form row labels via QFormLayout.
        self._form.labelForField(self._title_edit.parentWidget()).setText(
            tr("entry.field.title") + ":"
        )
        self._form.labelForField(self._url_edit).setText(tr("entry.field.url") + ":")
        self._form.labelForField(self._username_edit).setText(tr("entry.field.username") + ":")
        self._form.labelForField(self._password_edit.parentWidget()).setText(
            tr("entry.field.password") + ":"
        )
        self._form.labelForField(self._notes_edit).setText(tr("entry.field.notes") + ":")
        self._form.labelForField(self._tags_label).setText(tr("entry.field.tags") + ":")

        self._star_btn.setToolTip(tr("entry.button.favorite_tooltip"))

        # Eye button text depends on current visibility state.
        if self._eye_btn.isChecked():
            self._eye_btn.setText(tr("entry.button.hide"))
        else:
            self._eye_btn.setText(tr("entry.button.show"))
        self._eye_btn.setToolTip(tr("entry.button.show_hide_tooltip"))

        self._copy_btn.setText(tr("entry.button.copy"))
        self._copy_btn.setToolTip(tr("entry.button.copy_tooltip"))

        self._edit_btn.setText(tr("entry.button.edit"))
        self._edit_btn.setToolTip(tr("entry.button.edit_tooltip"))
        self._delete_btn.setText(tr("entry.button.delete"))
        self._delete_btn.setToolTip(tr("entry.button.delete_tooltip"))

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
            self._eye_btn.setText(tr("entry.button.hide"))
        else:
            self._password_edit.setEchoMode(QLineEdit.Password)
            self._eye_btn.setText(tr("entry.button.show"))

    def _on_copy_password(self) -> None:
        """Copy the password to the clipboard; auto-clear after 30 seconds.

        The QTimer is stored as self._clipboard_timer with self as Qt parent so
        it survives until it fires.  A new copy cancels any running timer.
        """
        text = self._password_edit.text()
        if not text:
            return

        QApplication.clipboard().setText(text)
        self.status_message.emit(tr("status.clipboard_copied"))

        if self._clipboard_timer is not None:
            self._clipboard_timer.stop()

        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.setSingleShot(True)
        self._clipboard_timer.timeout.connect(self._clear_clipboard)
        self._clipboard_timer.start(30_000)

    def _clear_clipboard(self) -> None:
        """Clear the clipboard after the 30-second timeout."""
        QApplication.clipboard().clear()
        self.status_message.emit(tr("status.clipboard_cleared"))
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
