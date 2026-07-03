"""Settings dialog: appearance, app info, and vault administration."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src import __version__
from src.db import Vault
from src.gui.title_bar import apply_title_bar
from src.gui.utils import get_build_date, get_git_short_hash
from src.i18n import tr


class SettingsDialog(QDialog):
    """Application settings with three sections: Appearance, About, and Danger Zone.

    Signals
    -------
    vault_reset_requested()
        Emitted when the user confirms a vault reset.
    theme_changed(str)
        Emitted with "dark" or "light" when the user changes the theme combo box.
    language_changed(str)
        Emitted with "de" or "en" when the user changes the language combo box.
    """

    vault_reset_requested = Signal()
    theme_changed = Signal(str)
    language_changed = Signal(str)

    def __init__(self, vault: Vault, parent: QWidget | None = None) -> None:
        """Build the dialog layout, pre-selecting persisted theme and language."""
        super().__init__(parent)
        self._vault = vault
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumWidth(500)
        self._init_ui()

    def showEvent(self, event: object) -> None:
        """Apply the themed title bar once the native window handle exists."""
        super().showEvent(event)
        apply_title_bar(self)

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Lay out all sections and the close button."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(self._build_appearance_section())
        layout.addWidget(self._build_about_section())
        layout.addWidget(self._build_danger_section())
        layout.addStretch()

        row = QHBoxLayout()
        row.addStretch()
        close_btn = QPushButton(tr("settings.close"))
        close_btn.clicked.connect(self.close)
        row.addWidget(close_btn)
        layout.addLayout(row)

    def _build_appearance_section(self) -> QGroupBox:
        """Build the 'Appearance' group with language and theme selectors."""
        box = QGroupBox(tr("settings.appearance"))
        form = QFormLayout(box)
        form.setSpacing(8)

        # Language selector — shown first so it is visually prominent.
        self._lang_combo = QComboBox()
        self._lang_combo.addItem(tr("settings.language_de"), userData="de")
        self._lang_combo.addItem(tr("settings.language_en"), userData="en")

        saved_lang = self._vault.get_meta("language")
        current_lang = saved_lang.decode() if saved_lang else "de"
        lang_idx = self._lang_combo.findData(current_lang)
        if lang_idx >= 0:
            self._lang_combo.setCurrentIndex(lang_idx)

        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        form.addRow(tr("settings.language"), self._lang_combo)

        # Theme selector.
        self._theme_combo = QComboBox()
        self._theme_combo.addItem(tr("settings.theme_dark"), userData="dark")
        self._theme_combo.addItem(tr("settings.theme_light"), userData="light")

        saved_theme = self._vault.get_meta("theme")
        current_theme = "light" if saved_theme == b"light" else "dark"
        theme_idx = self._theme_combo.findData(current_theme)
        if theme_idx >= 0:
            self._theme_combo.setCurrentIndex(theme_idx)

        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow(tr("settings.theme"), self._theme_combo)

        return box

    def _build_about_section(self) -> QGroupBox:
        """Build the 'About' group: app title, version, description, vault path."""
        box = QGroupBox(tr("settings.about"))
        vl = QVBoxLayout(box)
        vl.setSpacing(4)

        title_lbl = QLabel("PassSimple")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title_lbl.setFont(font)
        vl.addWidget(title_lbl)

        git_hash = get_git_short_hash()
        build_date = get_build_date()
        vl.addWidget(QLabel(f"Version {__version__} ({git_hash}) · {build_date}"))
        vl.addWidget(QLabel(tr("settings.about_description")))

        hotkey_lbl = QLabel(tr("settings.about_hotkey"))
        hotkey_lbl.setToolTip(tr("settings.about_hotkey_tooltip"))
        vl.addWidget(hotkey_lbl)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel(tr("settings.vault_location")))
        path_edit = QLineEdit(str(Vault.default_path()))
        path_edit.setReadOnly(True)
        path_row.addWidget(path_edit, 1)
        vl.addLayout(path_row)

        return box

    def _build_danger_section(self) -> QGroupBox:
        """Build the 'Danger zone' group."""
        box = QGroupBox(tr("settings.danger"))
        vl = QVBoxLayout(box)
        vl.setSpacing(8)

        reset_btn = QPushButton(tr("settings.reset_vault"))
        reset_btn.setObjectName("danger")
        reset_btn.setToolTip(tr("settings.reset_vault_tooltip"))
        reset_btn.clicked.connect(self._on_vault_reset)
        vl.addWidget(reset_btn)

        return box

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    def _on_theme_changed(self, index: int) -> None:
        """Emit theme_changed with the selected theme value."""
        value: str = self._theme_combo.itemData(index)
        self.theme_changed.emit(value)

    def _on_language_changed(self, index: int) -> None:
        """Emit language_changed with the selected language code."""
        value: str = self._lang_combo.itemData(index)
        self.language_changed.emit(value)

    def _on_vault_reset(self) -> None:
        """Ask for confirmation, then emit vault_reset_requested."""
        reset_box = QMessageBox(self)
        reset_box.setIcon(QMessageBox.Warning)
        reset_box.setWindowTitle(tr("settings.reset_vault_title"))
        reset_box.setText(tr("settings.reset_vault_text"))
        reset_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reset_box.setDefaultButton(QMessageBox.No)
        apply_title_bar(reset_box)
        if reset_box.exec() == QMessageBox.Yes:
            self.vault_reset_requested.emit()
            self.close()
