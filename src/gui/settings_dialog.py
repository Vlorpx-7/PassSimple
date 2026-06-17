"""Settings dialog: app info, CSV import, and vault administration."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.db import Vault
from src.importer import ImportResult, import_csv


class SettingsDialog(QDialog):
    """Application settings with three sections: About, CSV Import, Danger Zone.

    Signals
    -------
    entries_imported(list[Entry])
        Emitted after a successful CSV parse.  Each Entry carries
        password_ct=b"" and password=<plaintext>; the receiver must call
        Vault.add_entry to encrypt and persist.

    vault_reset_requested()
        Emitted when the user confirms a vault reset.  The receiver is
        responsible for deleting all entries and rotating the master key.
    """

    entries_imported = Signal(list)   # list[Entry]
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
        layout.addWidget(self._build_import_section())
        layout.addWidget(self._build_danger_section())
        layout.addStretch()

        # Close button — no OK/Cancel because actions are immediate.
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

    def _build_import_section(self) -> QGroupBox:
        """Build the 'CSV-Import' group."""
        box = QGroupBox("CSV-Import")
        vl = QVBoxLayout(box)
        vl.setSpacing(8)

        vl.addWidget(QLabel("Passwörter aus Chrome, Edge oder Brave importieren"))

        import_btn = QPushButton("CSV-Datei auswählen…")
        import_btn.setObjectName("primary")
        import_btn.clicked.connect(self._on_import_csv)
        vl.addWidget(import_btn)

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
    # CSV import flow
    # -----------------------------------------------------------------------

    def _on_import_csv(self) -> None:
        """Run the full import flow: warn → pick file → parse → report → offer delete."""
        # 1. Warn about plaintext content in the CSV.
        reply = QMessageBox.warning(
            self,
            "Sicherheitshinweis",
            "Achtung: Die CSV-Datei enthält Klartext-Passwörter.\n"
            "Bitte die Datei nach dem Import sicher löschen.",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok,
        )
        if reply != QMessageBox.Ok:
            return

        # 2. File picker.
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "CSV-Datei auswählen",
            "",
            "CSV-Dateien (*.csv);;Alle Dateien (*)",
        )
        if not path_str:
            return

        csv_path = Path(path_str)

        # 3. Parse the CSV.
        try:
            result: ImportResult = import_csv(csv_path)
        except Exception as e:
            QMessageBox.critical(self, "Importfehler", str(e))
            return

        if not result.entries:
            QMessageBox.information(
                self,
                "Import abgeschlossen",
                f"Keine Einträge importiert. {len(result.errors)} Fehler.",
            )
            return

        # 4. Hand entries to MainWindow for encryption and persistence.
        self.entries_imported.emit(result.entries)

        # 5. Show the result report.
        self._show_import_result(len(result.entries), result)

        # 6. Prompt to delete the source file — it still holds plaintext passwords.
        reply = QMessageBox.question(
            self,
            "Quelldatei löschen?",
            "Die Quelldatei enthält noch immer Klartext-Passwörter.\n"
            "Datei jetzt sicher löschen?\n\n"
            f"{csv_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            try:
                csv_path.unlink()
            except OSError as e:
                QMessageBox.warning(self, "Löschen fehlgeschlagen", str(e))

    def _show_import_result(self, imported: int, result: ImportResult) -> None:
        """Show a summary dialog; adds an error detail pane when failures occurred."""
        if not result.errors:
            QMessageBox.information(
                self,
                "Import abgeschlossen",
                f"{imported} Eintrag/Einträge erfolgreich importiert.",
            )
            return

        # Custom dialog so we can embed a scrollable error list.
        dlg = QDialog(self)
        dlg.setWindowTitle("Import abgeschlossen")
        dlg.setMinimumWidth(480)
        vl = QVBoxLayout(dlg)
        vl.setSpacing(8)

        vl.addWidget(QLabel(
            f"{imported} Eintrag/Einträge importiert,  {len(result.errors)} übersprungen:"
        ))

        error_edit = QTextEdit()
        error_edit.setReadOnly(True)
        error_edit.setMaximumHeight(160)
        error_edit.setPlainText(
            "\n".join(f"Zeile {e.row_number}: {e.reason}" for e in result.errors)
        )
        vl.addWidget(error_edit)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("primary")
        ok_btn.clicked.connect(dlg.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        vl.addLayout(btn_row)

        dlg.exec()

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
