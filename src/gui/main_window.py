"""Main application window: sidebar (search + entry list) + detail pane."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src import crypto
from src.db import Vault
from src.gui.dialogs import EntryDialog, SettingsDialog
from src.models import Entry

_ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"


class MainWindow(QMainWindow):
    """Top-level application window for PassSimple."""

    def __init__(self, vault: Vault, master_key: bytes) -> None:
        """Initialise the main window.

        master_key is stored as a private instance variable — it is never
        exposed via Qt's setProperty() or any inspector-visible mechanism.
        """
        super().__init__()
        self._vault = vault
        self._master_key = master_key  # private — NOT a Qt property
        self._current_entry_id: int | None = None
        # Stored as instance variable so the GC cannot collect it before it fires.
        self._clipboard_timer: QTimer | None = None

        self._init_ui()
        self._load_stylesheet()
        self._refresh_entry_list()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Build and configure all widgets and layouts."""
        self.setWindowTitle("PassSimple")
        icon_path = _ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(1000, 600)

        self._build_menu_bar()

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_detail_pane())
        splitter.setSizes([280, 720])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.statusBar().showMessage("Bereit")

    def _build_menu_bar(self) -> None:
        """Add a 'Datei' menu with Settings and Quit actions."""
        file_menu: QMenu = self.menuBar().addMenu("Datei")

        settings_action = file_menu.addAction("Einstellungen…")
        settings_action.triggered.connect(self._on_settings)

        file_menu.addSeparator()

        quit_action = file_menu.addAction("Beenden")
        quit_action.triggered.connect(QApplication.quit)

    def _build_sidebar(self) -> QWidget:
        """Build the left sidebar: search field, entry list, new-entry button."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Suchen...")
        self._search_edit.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_edit)

        self._entry_list = QListWidget()
        self._entry_list.setSpacing(1)
        self._entry_list.currentItemChanged.connect(self._on_entry_selected)
        layout.addWidget(self._entry_list, 1)

        new_btn = QPushButton("+ Neuer Eintrag")
        new_btn.setObjectName("primary")
        new_btn.clicked.connect(self._on_new_entry)
        layout.addWidget(new_btn)

        return widget

    def _build_detail_pane(self) -> QWidget:
        """Build the right pane: read-only fields, password controls, action buttons."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self._title_edit = QLineEdit()
        self._title_edit.setReadOnly(True)
        form.addRow("Titel:", self._title_edit)

        self._url_edit = QLineEdit()
        self._url_edit.setReadOnly(True)
        form.addRow("URL:", self._url_edit)

        self._username_edit = QLineEdit()
        self._username_edit.setReadOnly(True)
        form.addRow("Username:", self._username_edit)

        form.addRow("Passwort:", self._build_password_row())

        self._notes_edit = QTextEdit()
        self._notes_edit.setReadOnly(True)
        self._notes_edit.setMaximumHeight(100)
        form.addRow("Notizen:", self._notes_edit)

        self._tags_label = QLabel()
        self._tags_label.setWordWrap(True)
        form.addRow("Tags:", self._tags_label)

        layout.addLayout(form)
        layout.addLayout(self._build_action_buttons())
        layout.addStretch()

        self._set_detail_enabled(False)
        return widget

    def _build_password_row(self) -> QWidget:
        """Build the password field with eye-toggle and copy-to-clipboard button."""
        widget = QWidget()
        hl = QHBoxLayout(widget)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)

        self._password_edit = QLineEdit()
        self._password_edit.setReadOnly(True)
        self._password_edit.setEchoMode(QLineEdit.Password)
        hl.addWidget(self._password_edit, 1)

        self._eye_btn = QPushButton("Anzeigen")
        self._eye_btn.setCheckable(True)
        self._eye_btn.setFixedWidth(80)
        self._eye_btn.toggled.connect(self._on_eye_toggled)
        hl.addWidget(self._eye_btn)

        self._copy_btn = QPushButton("Kopieren")
        self._copy_btn.setFixedWidth(80)
        self._copy_btn.clicked.connect(self._on_copy_password)
        hl.addWidget(self._copy_btn)

        return widget

    def _build_action_buttons(self) -> QHBoxLayout:
        """Build the Bearbeiten and Loeschen action buttons."""
        hl = QHBoxLayout()
        self._edit_btn = QPushButton("Bearbeiten")
        self._edit_btn.clicked.connect(self._on_edit_entry)
        self._delete_btn = QPushButton("Loeschen")
        self._delete_btn.setObjectName("danger")
        self._delete_btn.clicked.connect(self._on_delete_entry)
        hl.addWidget(self._edit_btn)
        hl.addWidget(self._delete_btn)
        hl.addStretch()
        return hl

    # -----------------------------------------------------------------------
    # Stylesheet
    # -----------------------------------------------------------------------

    def _load_stylesheet(self) -> None:
        """Load and apply styles.qss from the same directory as this module."""
        qss_path = Path(__file__).parent / "styles.qss"
        try:
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except OSError:
            pass

    # -----------------------------------------------------------------------
    # Entry list
    # -----------------------------------------------------------------------

    def _refresh_entry_list(self, select_id: int | None = None) -> None:
        """Reload the full entry list from the vault and restore the selection."""
        saved_id = select_id if select_id is not None else self._current_entry_id
        try:
            entries = self._vault.list_entries()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        self._populate_entry_list(entries)
        self._restore_selection(saved_id)

    def _populate_entry_list(self, entries: list[Entry]) -> None:
        """Fill the QListWidget with entry items.

        Signals are blocked during the rebuild so intermediate currentItemChanged
        emissions don't trigger vault calls while the list is in a partial state.
        """
        self._entry_list.blockSignals(True)
        self._entry_list.clear()
        for entry in entries:
            item = QListWidgetItem(self._entry_list)
            item.setData(Qt.UserRole, entry.id)
            item.setSizeHint(QSize(0, 52))

            container = QWidget()
            vl = QVBoxLayout(container)
            vl.setContentsMargins(8, 4, 8, 4)
            vl.setSpacing(0)
            vl.addWidget(QLabel(entry.title))
            sub = QLabel(entry.username or "")
            sub.setObjectName("entrySubtitle")
            vl.addWidget(sub)
            self._entry_list.setItemWidget(item, container)

        self._entry_list.blockSignals(False)

    def _restore_selection(self, entry_id: int | None) -> None:
        """Re-select an entry by id after a list rebuild; clear the pane if not found."""
        if entry_id is not None:
            for i in range(self._entry_list.count()):
                item = self._entry_list.item(i)
                if item and item.data(Qt.UserRole) == entry_id:
                    self._entry_list.setCurrentItem(item)
                    return
        self._clear_detail()

    # -----------------------------------------------------------------------
    # Detail pane helpers
    # -----------------------------------------------------------------------

    def _load_entry_into_detail(self, entry: Entry) -> None:
        """Populate the detail pane with an entry's decrypted data."""
        self._current_entry_id = entry.id
        self._title_edit.setText(entry.title)
        self._url_edit.setText(entry.url or "")
        self._username_edit.setText(entry.username or "")
        self._password_edit.setText(entry.password or "")
        self._notes_edit.setPlainText(entry.notes or "")
        self._tags_label.setText(", ".join(t.name for t in entry.tags))

        # Reset the eye toggle whenever a new entry is loaded.
        self._eye_btn.blockSignals(True)
        self._eye_btn.setChecked(False)
        self._eye_btn.setText("Anzeigen")
        self._eye_btn.blockSignals(False)
        self._password_edit.setEchoMode(QLineEdit.Password)

        self._set_detail_enabled(True)

    def _clear_detail(self) -> None:
        """Clear and disable the detail pane."""
        self._current_entry_id = None
        self._title_edit.clear()
        self._url_edit.clear()
        self._username_edit.clear()
        self._password_edit.clear()
        self._notes_edit.clear()
        self._tags_label.clear()
        self._set_detail_enabled(False)

    def _set_detail_enabled(self, enabled: bool) -> None:
        """Enable or disable every interactive widget in the detail pane."""
        for widget in (
            self._url_edit,
            self._username_edit,
            self._password_edit,
            self._eye_btn,
            self._copy_btn,
            self._notes_edit,
            self._tags_label,
            self._edit_btn,
            self._delete_btn,
        ):
            widget.setEnabled(enabled)

    # -----------------------------------------------------------------------
    # Password field controls
    # -----------------------------------------------------------------------

    def _on_eye_toggled(self, checked: bool) -> None:
        """Toggle the password field between masked and visible mode."""
        if checked:
            self._password_edit.setEchoMode(QLineEdit.Normal)
            self._eye_btn.setText("Verbergen")
        else:
            self._password_edit.setEchoMode(QLineEdit.Password)
            self._eye_btn.setText("Anzeigen")

    def _on_copy_password(self) -> None:
        """Copy the password to the clipboard and schedule a 30-second auto-clear.

        The QTimer is stored as self._clipboard_timer (with self as Qt parent) to
        prevent Python's GC from collecting it before it fires.  A new copy
        cancels any still-running timer from a previous copy.
        """
        password_text = self._password_edit.text()
        if not password_text:
            return

        QApplication.clipboard().setText(password_text)
        self.statusBar().showMessage("In Zwischenablage kopiert — wird in 30 s geloescht")

        # Cancel any running timer before creating a fresh one.
        if self._clipboard_timer is not None:
            self._clipboard_timer.stop()

        # parent=self keeps the timer alive in Qt's object tree as well.
        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.setSingleShot(True)
        self._clipboard_timer.timeout.connect(self._clear_clipboard)
        self._clipboard_timer.start(30_000)

    def _clear_clipboard(self) -> None:
        """Clear the clipboard after the 30-second timeout."""
        QApplication.clipboard().clear()
        self.statusBar().showMessage("Zwischenablage geloescht")
        self._clipboard_timer = None

    # -----------------------------------------------------------------------
    # Sidebar signal handlers
    # -----------------------------------------------------------------------

    def _on_search_changed(self, text: str) -> None:
        """Re-filter the entry list on every keystroke."""
        # Save before populate — blockSignals prevents _on_entry_selected from
        # resetting _current_entry_id to None during the list rebuild.
        saved_id = self._current_entry_id
        try:
            entries = self._vault.search_entries(text) if text else self._vault.list_entries()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        self._populate_entry_list(entries)
        self._restore_selection(saved_id)

    def _on_entry_selected(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        """Load the selected entry into the detail pane, decrypting its password."""
        if current is None:
            self._clear_detail()
            return
        entry_id: int | None = current.data(Qt.UserRole)
        if entry_id is None:
            self._clear_detail()
            return
        try:
            entry = self._vault.get_entry(entry_id)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        if entry is None:
            self._clear_detail()
            return
        self._load_entry_into_detail(entry)

    # -----------------------------------------------------------------------
    # Detail pane action handlers
    # -----------------------------------------------------------------------

    def _on_new_entry(self) -> None:
        """Open the entry dialog and add the result to the vault."""
        dialog = EntryDialog(parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.get_entry()

        try:
            entry_id = self._vault.add_entry(
                data.title,
                data.password or "",
                username=data.username or None,
                url=data.url or None,
                notes=data.notes or None,
                tag_names=[t.name for t in data.tags] if data.tags else None,
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        self._refresh_entry_list(select_id=entry_id)

    def _on_edit_entry(self) -> None:
        """Open the entry dialog pre-filled with the current entry and persist changes."""
        if self._current_entry_id is None:
            return
        try:
            current = self._vault.get_entry(self._current_entry_id)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        if current is None:
            return

        dialog = EntryDialog(entry=current, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        data = dialog.get_entry()
        # ID muss übernommen werden, sonst geht der UPDATE ins Leere
        data.id = current.id
        # Ciphertext aus dem Dialog ist b"" — wir reichen das Klartext-Passwort als
        # new_password durch, damit update_entry es frisch verschlüsselt (mit neuer Nonce).
        try:
            self._vault.update_entry(data, new_password=data.password)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        self._refresh_entry_list(select_id=current.id)

    def _on_delete_entry(self) -> None:
        """Ask for confirmation, then permanently delete the selected entry."""
        if self._current_entry_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Eintrag loeschen",
            "Eintrag wirklich loeschen? Diese Aktion kann nicht rueckgaengig gemacht werden.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self._vault.delete_entry(self._current_entry_id)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        self._current_entry_id = None
        self._refresh_entry_list()

    # -----------------------------------------------------------------------
    # Settings dialog + signal handlers
    # -----------------------------------------------------------------------

    def _on_settings(self) -> None:
        """Open the settings dialog and wire up its signals."""
        dlg = SettingsDialog(parent=self)
        dlg.entries_imported.connect(self._on_entries_imported)
        dlg.vault_reset_requested.connect(self._on_vault_reset_requested)
        dlg.exec()

    def _on_entries_imported(self, entries: list) -> None:
        """Encrypt and persist every entry emitted by SettingsDialog.entries_imported."""
        added = 0
        failed = 0
        for entry in entries:
            try:
                self._vault.add_entry(
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
        self._refresh_entry_list()
        if failed:
            self.statusBar().showMessage(f"{added} importiert, {failed} Fehler.")
        else:
            self.statusBar().showMessage(f"{added} Einträge importiert.")

    def _on_vault_reset_requested(self) -> None:
        """Delete all entries and rotate the DPAPI-protected master key.

        The Vault class has no built-in key-rotation API, so the sequence is:
        1. Delete all entries via the public CRUD methods.
        2. Generate + DPAPI-protect a new master key.
        3. Close the vault, update vault_meta via a raw sqlite3 connection,
           then reopen with the new key.
        """
        # 1. Delete every entry through the public API.
        try:
            for entry in self._vault.list_entries():
                self._vault.delete_entry(entry.id)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        # 2. Generate and protect a new master key.
        try:
            new_key = crypto.generate_master_key()
            new_blob = crypto.protect_master_key(new_key)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        # 3. Persist the new DPAPI blob.  We close the vault first so both
        #    connections don't hold the WAL file at the same time.
        db_path = Vault.default_path()
        self._vault.close()
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    "UPDATE vault_meta SET value = ? WHERE key = ?",
                    (new_blob, "dpapi_master_key"),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        # 4. Reopen the vault with the rotated key.
        try:
            self._vault.open(new_key, path=db_path)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        self._master_key = new_key
        self._clear_detail()
        self._refresh_entry_list()
        self.statusBar().showMessage("Vault zurückgesetzt — neuer DPAPI-Schlüssel aktiv.")
