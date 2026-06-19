"""Standalone CSV import flow: warn → pick → parse → persist → report → offer delete."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.db import Vault
from src.importer import ImportResult, import_csv


def run_csv_import(parent: QWidget, vault: Vault) -> int:
    """Run the full CSV import flow and persist entries to the vault.

    Steps: security warning → file picker → parse → vault.add_entry for each row
    → result report → prompt to delete source file.

    Returns the number of successfully imported entries (0 if cancelled at any step).
    """
    # 1. Warn about plaintext content.
    reply = QMessageBox.warning(
        parent,
        "Sicherheitshinweis",
        "Achtung: Die CSV-Datei enthält Klartext-Passwörter.\n"
        "Bitte die Datei nach dem Import sicher löschen.",
        QMessageBox.Ok | QMessageBox.Cancel,
        QMessageBox.Ok,
    )
    if reply != QMessageBox.Ok:
        return 0

    # 2. File picker.
    path_str, _ = QFileDialog.getOpenFileName(
        parent,
        "CSV-Datei auswählen",
        "",
        "CSV-Dateien (*.csv);;Alle Dateien (*)",
    )
    if not path_str:
        return 0

    csv_path = Path(path_str)

    # 3. Parse.
    try:
        result: ImportResult = import_csv(csv_path)
    except Exception as e:
        QMessageBox.critical(parent, "Importfehler", str(e))
        return 0

    if not result.entries:
        QMessageBox.information(
            parent,
            "Import abgeschlossen",
            f"Keine Einträge importiert. {len(result.errors)} Fehler.",
        )
        return 0

    # 4. Persist to vault.
    added = 0
    failed = 0
    for entry in result.entries:
        try:
            vault.add_entry(
                entry.title,
                entry.password or "",
                username=entry.username or None,
                url=entry.url or None,
                notes=entry.notes,
                tag_names=None,
            )
            added += 1
        except Exception:
            failed += 1

    # 5. Result report.
    _show_import_result(parent, added, result)

    # 6. Prompt to delete source — it still holds plaintext passwords.
    reply = QMessageBox.question(
        parent,
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
            QMessageBox.warning(parent, "Löschen fehlgeschlagen", str(e))

    return added


def _show_import_result(parent: QWidget, imported: int, result: ImportResult) -> None:
    """Show a summary dialog; adds a scrollable error list when rows were skipped."""
    if not result.errors:
        QMessageBox.information(
            parent,
            "Import abgeschlossen",
            f"{imported} Eintrag/Einträge erfolgreich importiert.",
        )
        return

    dlg = QDialog(parent)
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
