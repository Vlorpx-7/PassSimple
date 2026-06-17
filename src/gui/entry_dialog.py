"""Dialog for creating and editing vault entries, with an integrated password generator."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.generator import _SYMBOLS, entropy_bits, generate_password
from src.models import Entry, Tag


class PasswordGeneratorDialog(QDialog):
    """Sub-dialog for configuring and generating a password.

    Opens with a freshly generated password; the user can adjust settings and
    click "Neu generieren" as many times as desired before accepting.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise settings with safe defaults and immediately generate a first password."""
        super().__init__(parent)
        self.setWindowTitle("Passwort generieren")
        self.setMinimumWidth(420)
        self._init_ui()
        self._generate()

    def _init_ui(self) -> None:
        """Build the layout: settings form, preview, entropy hint, action buttons."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(6)

        self._length_spin = QSpinBox()
        self._length_spin.setRange(16, 64)
        self._length_spin.setValue(20)
        form.addRow("Länge:", self._length_spin)

        self._cb_lower = QCheckBox("Kleinbuchstaben  (a–z)")
        self._cb_lower.setChecked(True)
        self._cb_upper = QCheckBox("Grossbuchstaben  (A–Z)")
        self._cb_upper.setChecked(True)
        self._cb_digits = QCheckBox("Ziffern  (0–9)")
        self._cb_digits.setChecked(True)
        self._cb_symbols = QCheckBox("Sonderzeichen  (!@#…)")
        self._cb_symbols.setChecked(True)
        self._cb_no_ambiguous = QCheckBox("Mehrdeutige Zeichen ausschliessen  (0/O/l/1/|…)")
        self._cb_no_ambiguous.setChecked(False)

        for cb in (
            self._cb_lower,
            self._cb_upper,
            self._cb_digits,
            self._cb_symbols,
            self._cb_no_ambiguous,
        ):
            form.addRow("", cb)

        layout.addLayout(form)

        self._preview = QLineEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(QFont("Courier New", 11))
        layout.addWidget(self._preview)

        self._entropy_label = QLabel()
        layout.addWidget(self._entropy_label)

        regen_btn = QPushButton("Neu generieren")
        regen_btn.clicked.connect(self._generate)
        layout.addWidget(regen_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _generate(self) -> None:
        """Generate a new password from the current settings and refresh the preview."""
        try:
            pw = generate_password(
                self._length_spin.value(),
                lowercase=self._cb_lower.isChecked(),
                uppercase=self._cb_upper.isChecked(),
                digits=self._cb_digits.isChecked(),
                symbols=self._cb_symbols.isChecked(),
                exclude_ambiguous=self._cb_no_ambiguous.isChecked(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Fehler", str(exc))
            return

        self._preview.setText(pw)

        alph = self._alphabet_size()
        bits = entropy_bits(len(pw), alph) if alph else 0.0
        self._entropy_label.setText(f"Entropie: ~{bits:.0f} bit")

    def _alphabet_size(self) -> int:
        """Count the effective alphabet size given the current settings."""
        excl = set("0Oo1lI|`") if self._cb_no_ambiguous.isChecked() else set()
        size = 0
        if self._cb_lower.isChecked():
            size += sum(1 for c in "abcdefghijklmnopqrstuvwxyz" if c not in excl)
        if self._cb_upper.isChecked():
            size += sum(1 for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in excl)
        if self._cb_digits.isChecked():
            size += sum(1 for c in "0123456789" if c not in excl)
        if self._cb_symbols.isChecked():
            size += sum(1 for c in _SYMBOLS if c not in excl)
        return size

    @property
    def password(self) -> str:
        """Return the password currently shown in the preview field."""
        return self._preview.text()


class EntryDialog(QDialog):
    """Modal dialog for creating (entry=None) or editing (entry=<Entry>) a vault entry."""

    def __init__(self, parent: QWidget | None = None, entry: Entry | None = None) -> None:
        """Prepare the form. Pass entry to pre-fill fields in edit mode."""
        super().__init__(parent)
        self._entry = entry
        # Holds the password snapshot taken in accept() just before the widget is cleared.
        # Properties and get_entry() read from here, never from the cleared widget.
        self._final_password: str = ""

        self.setWindowTitle("Eintrag bearbeiten" if entry is not None else "Neuer Eintrag")
        self.setMinimumWidth(500)

        self._init_ui()
        if entry is not None:
            self._populate(entry)

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
        self._title_edit.setPlaceholderText("Pflichtfeld")
        form.addRow("Titel:", self._title_edit)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://…")
        form.addRow("URL:", self._url_edit)

        self._username_edit = QLineEdit()
        form.addRow("Username:", self._username_edit)

        form.addRow("Passwort:", self._build_password_row())

        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)
        form.addRow("Notizen:", self._notes_edit)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("work, dev, personal")
        form.addRow("Tags:", self._tags_edit)

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

        self._eye_btn = QPushButton("Anzeigen")
        self._eye_btn.setCheckable(True)
        self._eye_btn.setFixedWidth(80)
        self._eye_btn.toggled.connect(self._on_eye_toggled)
        hl.addWidget(self._eye_btn)

        gen_btn = QPushButton("Generieren")
        gen_btn.setFixedWidth(90)
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
            self._eye_btn.setText("Verbergen")
        else:
            self._password_edit.setEchoMode(QLineEdit.Password)
            self._eye_btn.setText("Anzeigen")

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
            QMessageBox.warning(self, "Eingabe fehlt", "Titel darf nicht leer sein.")
            return
        if not self._password_edit.text():
            QMessageBox.warning(self, "Eingabe fehlt", "Passwort darf nicht leer sein.")
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
