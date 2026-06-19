"""Settings dialog: app info and vault administration."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.db import Vault


class SettingsDialog(QDialog):
    """Application settings with two sections: About and Danger Zone.

    Signals
    -------
    vault_reset_requested()
        Emitted when the user confirms a vault reset.  The receiver is
        responsible for deleting all entries and rotating the master key.
    """

    vault_reset_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the dialog layout."""
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(500)
        self._init_ui()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Lay out all sections and the close button."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(self._build_about_section())
        layout.addWidget(self._build_danger_section())
        layout.addStretch()

        row = QHBoxLayout()
        row.addStretch()
        close_btn = QPushButton("Schliessen")
        close_btn.clicked.connect(self.close)
        row.addWidget(close_btn)
        layout.addLayout(row)

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

        vl.addWidget(QLabel("Version 0.1.0"))
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
        reset_btn.clicked.connect(self._on_vault_reset)
        vl.addWidget(reset_btn)

        return box

    # -----------------------------------------------------------------------
    # Vault reset
    # -----------------------------------------------------------------------

    def _on_vault_reset(self) -> None:
        """Ask for confirmation, then emit vault_reset_requested."""
        reply = QMessageBox.warning(
            self,
            "Vault zurücksetzen",
            "Alle Einträge werden gelöscht und der DPAPI-Schlüssel neu erzeugt.\n"
            "Diese Aktion kann nicht rückgängig gemacht werden.\n\nSicher?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.vault_reset_requested.emit()
            self.close()
