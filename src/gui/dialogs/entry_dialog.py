"""Dialog for creating and editing vault entries."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.dialogs.password_generator_dialog import PasswordGeneratorDialog
from src.gui.title_bar import apply_title_bar
from src.i18n import tr
from src.models import Entry, Tag


class EntryDialog(QDialog):
    """Modal dialog for creating (entry=None) or editing (entry=<Entry>) a vault entry."""

    def __init__(self, parent: QWidget | None = None, entry: Entry | None = None) -> None:
        """Prepare the form. Pass entry to pre-fill fields in edit mode."""
        super().__init__(parent)
        self._entry = entry
        # Holds the password snapshot taken in accept() just before the widget is cleared.
        # Properties and get_entry() read from here, never from the cleared widget.
        self._final_password: str = ""

        self.setWindowTitle(
            tr("entry.dialog_title_edit") if entry is not None else tr("entry.dialog_title_new")
        )
        self.setMinimumWidth(500)

        self._init_ui()
        if entry is not None:
            self._populate(entry)

    def showEvent(self, event: object) -> None:
        """Apply the themed title bar once the native window handle exists."""
        super().showEvent(event)
        apply_title_bar(self)

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Build the form layout with all fields and the OK / Cancel button box."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText(tr("entry.placeholder.title"))
        form.addRow(tr("entry.field.title") + ":", self._title_edit)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText(tr("entry.placeholder.url"))
        form.addRow(tr("entry.field.url") + ":", self._url_edit)

        self._username_edit = QLineEdit()
        form.addRow(tr("entry.field.username") + ":", self._username_edit)

        form.addRow(tr("entry.field.password") + ":", self._build_password_row())

        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)
        form.addRow(tr("entry.field.notes") + ":", self._notes_edit)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText(tr("entry.placeholder.tags"))
        form.addRow(tr("entry.field.tags") + ":", self._tags_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_password_row(self) -> QWidget:
        """Build the password field with eye-toggle and generator button."""
        widget = QWidget()
        hl = QHBoxLayout(widget)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.Password)
        hl.addWidget(self._password_edit, 1)

        self._eye_btn = QPushButton(tr("entry.button.show"))
        self._eye_btn.setCheckable(True)
        self._eye_btn.setFixedWidth(80)
        self._eye_btn.setToolTip(tr("entry.button.show_hide_tooltip"))
        self._eye_btn.toggled.connect(self._on_eye_toggled)
        hl.addWidget(self._eye_btn)

        gen_btn = QPushButton(tr("entry.button.generate"))
        gen_btn.setFixedWidth(90)
        gen_btn.setToolTip(tr("entry.button.generate_tooltip"))
        gen_btn.clicked.connect(self._on_generate)
        hl.addWidget(gen_btn)

        return widget

    def _populate(self, entry: Entry) -> None:
        """Pre-fill all fields from an existing entry."""
        self._title_edit.setText(entry.title)
        self._url_edit.setText(entry.url or "")
        self._username_edit.setText(entry.username or "")
        self._password_edit.setText(entry.password or "")
        self._notes_edit.setPlainText(entry.notes or "")
        self._tags_edit.setText(", ".join(t.name for t in entry.tags))

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    def _on_eye_toggled(self, checked: bool) -> None:
        """Toggle the password field between masked and visible."""
        if checked:
            self._password_edit.setEchoMode(QLineEdit.Normal)
            self._eye_btn.setText(tr("entry.button.hide"))
        else:
            self._password_edit.setEchoMode(QLineEdit.Password)
            self._eye_btn.setText(tr("entry.button.show"))

    def _on_generate(self) -> None:
        """Open the password generator sub-dialog and apply the result."""
        dlg = PasswordGeneratorDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._password_edit.setText(dlg.password)

    # -----------------------------------------------------------------------
    # Accept / reject — password hygiene
    # -----------------------------------------------------------------------

    def accept(self) -> None:
        """Validate required fields; if OK, snapshot the password and close."""
        if not self._title_edit.text().strip():
            QMessageBox.warning(
                self,
                tr("entry.validation.missing_title"),
                tr("entry.validation.missing_title_text"),
            )
            return
        if not self._password_edit.text():
            QMessageBox.warning(
                self,
                tr("entry.validation.missing_password"),
                tr("entry.validation.missing_password_text"),
            )
            return

        # Read before clearing — password must not stay in the widget longer than needed.
        self._final_password = self._password_edit.text()
        self._password_edit.clear()
        super().accept()

    def reject(self) -> None:
        """Clear the password field before dismissing."""
        self._password_edit.clear()
        super().reject()

    # -----------------------------------------------------------------------
    # Properties (intended to be read after exec() returns Accepted)
    # -----------------------------------------------------------------------

    @property
    def title(self) -> str:
        """Stripped title text."""
        return self._title_edit.text().strip()

    @property
    def url(self) -> str | None:
        """Stripped URL, or None if blank."""
        v = self._url_edit.text().strip()
        return v or None

    @property
    def username(self) -> str | None:
        """Stripped username, or None if blank."""
        v = self._username_edit.text().strip()
        return v or None

    @property
    def password(self) -> str:
        """The password as entered; populated only after accept()."""
        return self._final_password

    @property
    def notes(self) -> str | None:
        """Stripped notes text, or None if blank."""
        v = self._notes_edit.toPlainText().strip()
        return v or None

    @property
    def tag_names(self) -> list[str]:
        """Comma-separated tags split, stripped, and filtered of empty strings."""
        return [t.strip() for t in self._tags_edit.text().split(",") if t.strip()]

    # -----------------------------------------------------------------------
    # Entry factory
    # -----------------------------------------------------------------------

    def get_entry(self) -> Entry:
        """Return a new Entry built from the current field values.

        password_ct is always b'' here — Vault.add_entry / Vault.update_entry
        will encrypt it.  password carries the plaintext from the password
        property (non-empty only after accept()).
        """
        return Entry(
            id=None,
            title=self.title,
            username=self.username,
            password_ct=b"",
            url=self.url,
            notes=self.notes,
            created_at="",
            updated_at="",
            tags=[Tag(id=None, name=n) for n in self.tag_names],
            password=self.password,
        )
