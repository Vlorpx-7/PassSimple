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
from src.gui.title_bar import apply_title_bar
from src.gui.utils import plural_entries
from src.importer import ImportResult, import_csv


def run_csv_import(parent: QWidget, vault: Vault) -> int:
    """Run the full CSV import flow and persist entries to the vault.

    Steps: security warning → file picker → parse → vault.add_entry for each row
    → result report → prompt to delete source file.

    Returns the number of successfully imported entries (0 if cancelled at any step).
    """
    # 1. Warn about plaintext content.
    warn_box = QMessageBox(parent)
    warn_box.setIcon(QMessageBox.Warning)
    warn_box.setWindowTitle("Sicherheitshinweis")
    warn_box.setText(
        "Achtung: Die CSV-Datei enthält Klartext-Passwörter.\n"
        "Bitte die Datei nach dem Import sicher löschen."
    )
    warn_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    warn_box.setDefaultButton(QMessageBox.Ok)
    apply_title_bar(warn_box)
    if warn_box.exec() != QMessageBox.Ok:
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

    # 4. Persist to vault, skipping duplicates.
    added = 0
    failed = 0
    dup_details: list[tuple[int, str]] = []  # (row_num, title) for report

    # enumerate starting at 2 matches the importer's row numbering (row 1 = header).
    for row_num, entry in enumerate(result.entries, start=2):
        try:
            existing_id = vault.find_duplicate(
                title=entry.title,
                username=entry.username,
                url=entry.url,
                password=entry.password or "",
            )
            if existing_id is not None:
                dup_details.append((row_num, entry.title))
                continue
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
    _show_import_result(parent, added, result, dup_details)

    # 6. Prompt to delete source — it still holds plaintext passwords.
    del_box = QMessageBox(parent)
    del_box.setIcon(QMessageBox.Question)
    del_box.setWindowTitle("Quelldatei löschen?")
    del_box.setText(
        "Die Quelldatei enthält noch immer Klartext-Passwörter.\n"
        "Datei jetzt sicher löschen?\n\n"
        f"{csv_path}"
    )
    del_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    del_box.setDefaultButton(QMessageBox.Yes)
    apply_title_bar(del_box)
    if del_box.exec() == QMessageBox.Yes:
        try:
            csv_path.unlink()
        except OSError as e:
            QMessageBox.warning(parent, "Löschen fehlgeschlagen", str(e))

    return added


def _show_import_result(
    parent: QWidget,
    imported: int,
    result: ImportResult,
    dup_details: list[tuple[int, str]],
) -> None:
    """Show a summary dialog with import counts and a scrollable detail list.

    The detail list includes duplicate entries and parse errors.
    Shown as a simple QMessageBox when there is nothing to list.
    """
    dups_count = len(dup_details)
    errors_count = len(result.errors)

    parts = [f"{plural_entries(imported)} importiert"]
    if dups_count > 0:
        dup_word = "Duplikat" if dups_count == 1 else "Duplikate"
        parts.append(f"{dups_count} {dup_word} übersprungen")
    if errors_count > 0:
        parts.append(f"{errors_count} Fehler")
    summary = ", ".join(parts)

    if dups_count == 0 and errors_count == 0:
        QMessageBox.information(parent, "Import abgeschlossen", f"{summary}.")
        return

    dlg = QDialog(parent)
    dlg.setWindowTitle("Import abgeschlossen")
    apply_title_bar(dlg)
    dlg.setMinimumWidth(480)
    vl = QVBoxLayout(dlg)
    vl.setSpacing(8)

    vl.addWidget(QLabel(f"{summary}:"))

    lines: list[str] = [
        f"Zeile {row}: Duplikat (Titel: {title})" for row, title in dup_details
    ] + [
        f"Zeile {e.row_number}: {e.reason}" for e in result.errors
    ]
    detail_edit = QTextEdit()
    detail_edit.setReadOnly(True)
    detail_edit.setMaximumHeight(160)
    detail_edit.setPlainText("\n".join(lines))
    vl.addWidget(detail_edit)

    ok_btn = QPushButton("OK")
    ok_btn.setObjectName("primary")
    ok_btn.clicked.connect(dlg.accept)
    btn_row = QHBoxLayout()
    btn_row.addStretch()
    btn_row.addWidget(ok_btn)
    vl.addLayout(btn_row)

    dlg.exec()
