"""Dialog for configuring and generating a password."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.generator import _SYMBOLS, entropy_bits, generate_password
from src.gui.title_bar import apply_title_bar
from src.i18n import tr


class PasswordGeneratorDialog(QDialog):
    """Sub-dialog for configuring and generating a password.

    Opens with a freshly generated password; the user can adjust settings and
    click "Regenerate" as many times as desired before accepting.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise settings with safe defaults and immediately generate a first password."""
        super().__init__(parent)
        self.setWindowTitle(tr("generator.title"))
        self.setMinimumWidth(420)
        self._init_ui()
        self._generate()

    def showEvent(self, event: object) -> None:
        """Apply the themed title bar once the native window handle exists."""
        super().showEvent(event)
        apply_title_bar(self)

    def _init_ui(self) -> None:
        """Build the layout: settings form, preview, entropy hint, action buttons."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(6)

        self._length_spin = QSpinBox()
        self._length_spin.setRange(16, 64)
        self._length_spin.setValue(20)
        form.addRow(tr("generator.length"), self._length_spin)

        self._cb_lower = QCheckBox(tr("generator.lowercase"))
        self._cb_lower.setChecked(True)
        self._cb_upper = QCheckBox(tr("generator.uppercase"))
        self._cb_upper.setChecked(True)
        self._cb_digits = QCheckBox(tr("generator.digits"))
        self._cb_digits.setChecked(True)
        self._cb_symbols = QCheckBox(tr("generator.symbols"))
        self._cb_symbols.setChecked(True)
        self._cb_no_ambiguous = QCheckBox(tr("generator.no_ambiguous"))
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

        regen_btn = QPushButton(tr("generator.regenerate"))
        regen_btn.setToolTip(tr("generator.regenerate_tooltip"))
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
            QMessageBox.warning(self, tr("generator.error_title"), str(exc))
            return

        self._preview.setText(pw)

        alph = self._alphabet_size()
        bits = entropy_bits(len(pw), alph) if alph else 0.0
        self._entropy_label.setText(tr("generator.entropy").format(bits=f"{bits:.0f}"))

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
