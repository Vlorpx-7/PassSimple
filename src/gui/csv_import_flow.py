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
from src.i18n import tr
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
    warn_box.setWindowTitle(tr("import.warn_title"))
    warn_box.setText(tr("import.warn_text"))
    warn_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    warn_box.setDefaultButton(QMessageBox.Ok)
    apply_title_bar(warn_box)
    if warn_box.exec() != QMessageBox.Ok:
        return 0

    # 2. File picker.
    path_str, _ = QFileDialog.getOpenFileName(
        parent,
        tr("import.file_dialog_title"),
        "",
        tr("import.file_filter"),
    )
    if not path_str:
        return 0

    csv_path = Path(path_str)

    # 3. Parse.
    try:
        result: ImportResult = import_csv(csv_path)
    except Exception as e:
        QMessageBox.critical(parent, tr("import.error_title"), str(e))
        return 0

    if not result.entries:
        QMessageBox.information(
            parent,
            tr("import.done_title"),
            tr("import.empty_result").format(errors=len(result.errors)),
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
    del_box.setWindowTitle(tr("import.delete_source_title"))
    del_box.setText(tr("import.delete_source_text").format(path=csv_path))
    del_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    del_box.setDefaultButton(QMessageBox.Yes)
    apply_title_bar(del_box)
    if del_box.exec() == QMessageBox.Yes:
        try:
            csv_path.unlink()
        except OSError as e:
            QMessageBox.warning(parent, tr("import.delete_failed_title"), str(e))

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

    parts = [tr("import.result_imported").format(count=plural_entries(imported))]
    if dups_count > 0:
        dup_word = (
            tr("import.result_duplicate_singular")
            if dups_count == 1
            else tr("import.result_duplicate_plural")
        )
        parts.append(tr("import.result_skipped").format(count=dups_count, word=dup_word))
    if errors_count > 0:
        parts.append(tr("import.result_errors").format(count=errors_count))
    summary = ", ".join(parts)

    if dups_count == 0 and errors_count == 0:
        QMessageBox.information(parent, tr("import.done_title"), f"{summary}.")
        return

    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("import.done_title"))
    apply_title_bar(dlg)
    dlg.setMinimumWidth(480)
    vl = QVBoxLayout(dlg)
    vl.setSpacing(8)

    vl.addWidget(QLabel(f"{summary}:"))

    lines: list[str] = [
        tr("import.result_duplicate_line").format(row=row, title=title)
        for row, title in dup_details
    ] + [
        tr("import.result_error_line").format(row=e.row_number, reason=e.reason)
        for e in result.errors
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
