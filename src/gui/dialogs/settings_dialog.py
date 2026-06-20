"""Settings dialog: appearance, app info, and vault administration."""

from __future__ import annotations

from datetime import datetime

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
from src.gui.utils import get_git_short_hash


class SettingsDialog(QDialog):
    """Application settings with three sections: Appearance, About, and Danger Zone.

    Signals
    -------
    vault_reset_requested()
        Emitted when the user confirms a vault reset.
    theme_changed(str)
        Emitted with "dark" or "light" when the user changes the theme combo box.
        Connected to MainWindow.apply_theme so the change is live.
    """

    vault_reset_requested = Signal()
    theme_changed = Signal(str)

    def __init__(self, vault: Vault, parent: QWidget | None = None) -> None:
        """Build the dialog layout, pre-selecting the current theme from vault_meta."""
        super().__init__(parent)
        self._vault = vault
        self.setWindowTitle("Einstellungen")
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
        close_btn = QPushButton("Schliessen")
        close_btn.clicked.connect(self.close)
        row.addWidget(close_btn)
        layout.addLayout(row)

    def _build_appearance_section(self) -> QGroupBox:
        """Build the 'Erscheinungsbild' group with a theme selector."""
        box = QGroupBox("Erscheinungsbild")
        form = QFormLayout(box)
        form.setSpacing(8)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Dunkel", userData="dark")
        self._theme_combo.addItem("Hell", userData="light")

        # Pre-select the persisted theme; fall back to dark.
        saved = self._vault.get_meta("theme")
        current = "light" if saved == b"light" else "dark"
        index = self._theme_combo.findData(current)
        if index >= 0:
            self._theme_combo.setCurrentIndex(index)

        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow("Theme:", self._theme_combo)

        return box

    def _build_about_section(self) -> QGroupBox:
        """Build the 'Über' group: app title, version, description, vault path."""
        box = QGroupBox("Über")
        vl = QVBoxLayout(box)
        vl.setSpacing(4)

        title_lbl = QLabel("PassSimple")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title_lbl.setFont(font)
        vl.addWidget(title_lbl)

        git_hash = get_git_short_hash()
        build_date = datetime.now().strftime("%Y-%m-%d")
        vl.addWidget(QLabel(f"Version {__version__} ({git_hash}) · {build_date}"))
        vl.addWidget(QLabel("Lokaler Passwortmanager mit DPAPI-Verschlüsselung"))

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Vault-Speicherort:"))
        path_edit = QLineEdit(str(Vault.default_path()))
        path_edit.setReadOnly(True)
        path_row.addWidget(path_edit, 1)
        vl.addLayout(path_row)

        return box

    def _build_danger_section(self) -> QGroupBox:
        """Build the 'Gefährliche Aktionen' group."""
        box = QGroupBox("Gefährliche Aktionen")
        vl = QVBoxLayout(box)
        vl.setSpacing(8)

        reset_btn = QPushButton("Vault zurücksetzen")
        reset_btn.setObjectName("danger")
        reset_btn.setToolTip("Alle Einträge löschen und DPAPI-Schlüssel rotieren")
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

    def _on_vault_reset(self) -> None:
        """Ask for confirmation, then emit vault_reset_requested."""
        reset_box = QMessageBox(self)
        reset_box.setIcon(QMessageBox.Warning)
        reset_box.setWindowTitle("Vault zurücksetzen")
        reset_box.setText(
            "Alle Einträge werden gelöscht und der DPAPI-Schlüssel neu erzeugt.\n"
            "Diese Aktion kann nicht rückgängig gemacht werden.\n\nSicher?"
        )
        reset_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reset_box.setDefaultButton(QMessageBox.No)
        apply_title_bar(reset_box)
        if reset_box.exec() == QMessageBox.Yes:
            self.vault_reset_requested.emit()
            self.close()
