"""Main application window: 3-column layout (NavSidebar / EntryListPane / EntryDetailPane)."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import QMetaObject, Qt, Slot
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QWidget,
)

from src import crypto
from src.db import Vault
from src.gui.csv_import_flow import run_csv_import
from src.gui.utils import plural_entries
from src.gui.dialogs import EntryDialog, SettingsDialog
from src.gui.widgets.entry_detail_pane import EntryDetailPane
from src.gui.widgets.entry_list_pane import EntryListPane
from src.gui.title_bar import apply_title_bar, set_current_theme
from src.gui.quick_search import QuickSearchPopup
from src.gui.tray import AppTray
from src.gui.widgets.nav_sidebar import NavSidebar
from src.paths import resource_path


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
        self._current_filter: str = "all"
        self._current_sort: str = "title_asc"
        self._current_entry_id: int | None = None
        self._really_quit: bool = False
        self._hint_shown: bool = self._vault.get_meta("tray_hint_shown") is not None

        self._init_ui()
        self._load_stylesheet()

        # Restore persisted sort preference before the first load.
        sort_bytes = self._vault.get_meta("list_sort")
        if sort_bytes:
            self._current_sort = sort_bytes.decode()
        self._list_pane.set_sort(self._current_sort)

        # Load all entries into the list on startup.
        self._load_current_filter()

        # Tray must be created after the stylesheet is applied so the app icon
        # is already set on QApplication before we read it.
        self._tray = AppTray(self, QApplication.instance().windowIcon())
        self._tray.show()

        self._quick_search: QuickSearchPopup | None = None
        try:
            import keyboard  # type: ignore[import-untyped]
            keyboard.add_hotkey("ctrl+alt+p", self._on_global_hotkey)
        except Exception:
            pass  # Hotkey registration can fail on some systems; app still runs

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Build the 3-column layout and wire all signals."""
        self.setWindowTitle("")
        # Clear the per-window icon so the title bar stays clean.
        # The app-wide icon (set via QApplication.setWindowIcon in app.py)
        # continues to appear in the taskbar.
        transparent_pixmap = QPixmap(1, 1)
        transparent_pixmap.fill(Qt.GlobalColor.transparent)
        self.setWindowIcon(QIcon(transparent_pixmap))
        self.setMinimumSize(1100, 650)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._nav = NavSidebar(self)
        self._list_pane = EntryListPane(self)
        self._detail_pane = EntryDetailPane(self)

        layout.addWidget(self._nav)
        sep1 = QFrame()
        sep1.setObjectName("columnSeparator")
        sep1.setFrameShape(QFrame.Shape.NoFrame)
        sep1.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        layout.addWidget(sep1)
        layout.addWidget(self._list_pane)
        sep2 = QFrame()
        sep2.setObjectName("columnSeparator")
        sep2.setFrameShape(QFrame.Shape.NoFrame)
        sep2.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        layout.addWidget(sep2)
        layout.addWidget(self._detail_pane, 1)

        self._wire_signals()
        self.statusBar().showMessage("Bereit")

    def _wire_signals(self) -> None:
        """Connect all inter-widget signals."""
        self._nav.nav_changed.connect(self._on_nav_changed)
        self._list_pane.entry_selected.connect(self._on_entry_selected)
        self._list_pane.search_changed.connect(self._on_search_changed)
        self._list_pane.sort_changed.connect(self._on_sort_changed)
        self._detail_pane.new_entry_requested.connect(self._on_new_entry)
        self._detail_pane.edit_entry_requested.connect(self._on_edit_entry)
        self._detail_pane.delete_entry_requested.connect(self._on_delete_entry)
        self._detail_pane.favorite_toggled.connect(self._on_favorite_toggled)
        self._detail_pane.status_message.connect(self.statusBar().showMessage)

    # -----------------------------------------------------------------------
    # Stylesheet
    # -----------------------------------------------------------------------

    def _load_stylesheet(self) -> None:
        """Load and apply the QSS file for the current theme (dark or light)."""
        theme = self._vault.get_meta("theme")
        filename = "styles_light.qss" if theme == b"light" else "styles_dark.qss"
        qss_path = resource_path(f"src/gui/{filename}")
        try:
            QApplication.instance().setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except OSError:
            pass

    def apply_theme(self, theme: str) -> None:
        """Persist theme choice, reload the stylesheet, and update the title bar live."""
        self._vault.set_meta("theme", theme.encode())
        set_current_theme(theme)
        self._load_stylesheet()
        apply_title_bar(self)

    def showEvent(self, event: object) -> None:
        """Apply the title bar style once the native window handle exists."""
        super().showEvent(event)
        apply_title_bar(self)

    # -----------------------------------------------------------------------
    # Quick-search popup
    # -----------------------------------------------------------------------

    @Slot()
    def show_quick_search(self) -> None:
        """Show or focus the quick-search popup.

        Creates a new QuickSearchPopup if none is open; otherwise brings the
        existing one to the foreground.  Must be a @Slot so QMetaObject.invokeMethod
        can marshal calls from the keyboard background thread into the Qt main thread.
        """
        if self._quick_search is None or not self._quick_search.isVisible():
            self._quick_search = QuickSearchPopup(self._vault, parent=None)
        self._quick_search.show()
        self._quick_search.raise_()
        self._quick_search.activateWindow()

    def _on_global_hotkey(self) -> None:
        """Callback invoked by the keyboard library from a background thread.

        Must not touch Qt objects directly — marshals show_quick_search into
        the Qt main thread via a queued meta-method call.
        """
        QMetaObject.invokeMethod(self, "show_quick_search", Qt.ConnectionType.QueuedConnection)

    # -----------------------------------------------------------------------
    # Window close / tray behaviour
    # -----------------------------------------------------------------------

    def closeEvent(self, event: object) -> None:
        """Hide to tray instead of quitting, unless quit_application() was called."""
        if self._really_quit:
            event.accept()  # type: ignore[union-attr]
            return
        event.ignore()  # type: ignore[union-attr]
        self.hide()
        if not self._hint_shown:
            self._hint_shown = True
            self._vault.set_meta("tray_hint_shown", b"1")
            self._tray.showMessage(
                "PassSimple läuft im Hintergrund",
                "Klicke das Tray-Icon zum Öffnen.",
                self._tray.MessageIcon.Information,
                3000,
            )

    def quit_application(self) -> None:
        """Cleanly exit the app from anywhere (window visible or hidden in tray).

        Bypasses closeEvent entirely: hides the tray first (otherwise Qt keeps
        the event loop alive as long as a QSystemTrayIcon exists), then quits
        the event loop directly.
        """
        self._really_quit = True
        try:
            import keyboard  # type: ignore[import-untyped]
            keyboard.unhook_all()
        except Exception:
            pass
        self._tray.hide()
        QApplication.instance().quit()

    # -----------------------------------------------------------------------
    # Filter / list management
    # -----------------------------------------------------------------------

    def _load_current_filter(self, select_id: int | None = None) -> None:
        """Reload entries according to the active filter and restore the selection.

        If select_id is given it overrides _current_entry_id as the target.
        If the target entry is not in the filtered list the detail pane is cleared.
        """
        saved_id = select_id if select_id is not None else self._current_entry_id
        try:
            if self._current_filter == "favorites":
                entries = self._vault.list_favorites(sort=self._current_sort)
            else:
                entries = self._vault.list_entries(sort=self._current_sort)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        self._list_pane.set_entries(entries)

        if saved_id is not None:
            found = self._list_pane.select_entry(saved_id)
            if not found:
                # Entry is not in the filtered view — clear the detail pane.
                self._detail_pane.clear()
                self._current_entry_id = None
        else:
            self._detail_pane.clear()

    # -----------------------------------------------------------------------
    # Nav signal handler
    # -----------------------------------------------------------------------

    def _on_nav_changed(self, value: str) -> None:
        """Switch filter, run import, or open settings based on nav_changed value."""
        if value in ("all", "favorites"):
            self._current_filter = value
            self._current_entry_id = None
            self._detail_pane.clear()

            if value == "all":
                self._list_pane.set_empty_message("Keine Einträge vorhanden.")
            else:
                self._list_pane.set_empty_message(
                    "Noch keine Favoriten. Markiere einen Eintrag mit dem Stern, "
                    "um ihn hier zu sehen."
                )

            self._load_current_filter()

        elif value == "import":
            self._run_import()

        elif value == "settings":
            self._on_settings()

    # -----------------------------------------------------------------------
    # List pane signal handlers
    # -----------------------------------------------------------------------

    def _on_sort_changed(self, sort: str) -> None:
        """Persist the new sort order and reload the entry list."""
        self._current_sort = sort
        self._vault.set_meta("list_sort", sort.encode())
        self._load_current_filter()

    def _on_entry_selected(self, entry_id: int) -> None:
        """Load the selected entry into the detail pane, decrypting its password."""
        self._current_entry_id = entry_id
        try:
            entry = self._vault.get_entry(entry_id)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        if entry is None:
            self._detail_pane.clear()
            self._current_entry_id = None
            return
        self._detail_pane.load_entry(entry)

    def _on_search_changed(self, text: str) -> None:
        """Re-filter the entry list on every keystroke.

        Non-empty text: search across all entries regardless of current filter.
        Empty text: restore the active filter (all / favorites).
        """
        saved_id = self._current_entry_id
        try:
            if text:
                entries = self._vault.search_entries(text, sort=self._current_sort)
            elif self._current_filter == "favorites":
                entries = self._vault.list_favorites(sort=self._current_sort)
            else:
                entries = self._vault.list_entries(sort=self._current_sort)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        self._list_pane.set_entries(entries)
        if saved_id is not None:
            self._list_pane.select_entry(saved_id)

    # -----------------------------------------------------------------------
    # Detail pane signal handlers — CRUD
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
        self._current_entry_id = entry_id
        self._load_current_filter(select_id=entry_id)

    def _on_edit_entry(self, entry_id: int) -> None:
        """Open the entry dialog pre-filled with the current entry and persist changes."""
        try:
            current = self._vault.get_entry(entry_id)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        if current is None:
            return

        dialog = EntryDialog(entry=current, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        data = dialog.get_entry()
        # The ID must be carried over; the dialog's get_entry() returns id=None.
        data.id = current.id
        # Ciphertext from the dialog is b"" — pass plaintext as new_password so
        # update_entry re-encrypts with a fresh nonce.
        try:
            self._vault.update_entry(data, new_password=data.password)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        self._current_entry_id = current.id
        self._load_current_filter(select_id=current.id)

    def _on_delete_entry(self, entry_id: int) -> None:
        """Ask for confirmation, then permanently delete the entry."""
        del_box = QMessageBox(self)
        del_box.setIcon(QMessageBox.Question)
        del_box.setWindowTitle("Eintrag loeschen")
        del_box.setText("Eintrag wirklich loeschen? Diese Aktion kann nicht rueckgaengig gemacht werden.")
        del_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        del_box.setDefaultButton(QMessageBox.No)
        apply_title_bar(del_box)
        if del_box.exec() != QMessageBox.Yes:
            return
        try:
            self._vault.delete_entry(entry_id)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        self._current_entry_id = None
        self._detail_pane.clear()
        self._load_current_filter()

    # -----------------------------------------------------------------------
    # Detail pane signal handlers — favorites
    # -----------------------------------------------------------------------

    def _on_favorite_toggled(self, entry_id: int, is_favorite: bool) -> None:
        """Persist the favorite state and reload the current filtered view."""
        try:
            self._vault.set_favorite(entry_id, is_favorite)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        self._load_current_filter(select_id=entry_id)

    # -----------------------------------------------------------------------
    # CSV import
    # -----------------------------------------------------------------------

    def _run_import(self) -> None:
        """Run the standalone CSV import flow and refresh the list on success."""
        added = run_csv_import(self, self._vault)
        if added > 0:
            self._load_current_filter()
            self.statusBar().showMessage(f"{plural_entries(added)} importiert.")

    # -----------------------------------------------------------------------
    # Settings dialog + vault reset
    # -----------------------------------------------------------------------

    def _on_settings(self) -> None:
        """Open the settings dialog, wire vault reset and live theme signals."""
        dlg = SettingsDialog(vault=self._vault, parent=self)
        dlg.vault_reset_requested.connect(self._on_vault_reset_requested)
        dlg.theme_changed.connect(self.apply_theme)
        dlg.exec()

    def _on_vault_reset_requested(self) -> None:
        """Delete all entries and rotate the DPAPI-protected master key.

        The Vault class has no built-in key-rotation API, so the sequence is:
        1. Delete all entries via the public CRUD methods.
        2. Generate + DPAPI-protect a new master key.
        3. Close the vault, update vault_meta via a raw sqlite3 connection,
           then reopen with the new key.
        """
        try:
            for entry in self._vault.list_entries():
                self._vault.delete_entry(entry.id)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        try:
            new_key = crypto.generate_master_key()
            new_blob = crypto.protect_master_key(new_key)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        # Close the vault before opening a second connection to the same file.
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

        try:
            self._vault.open(new_key, path=db_path)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        self._master_key = new_key
        self._current_entry_id = None
        self._detail_pane.clear()
        self._load_current_filter()
        self.statusBar().showMessage("Vault zurückgesetzt — neuer DPAPI-Schlüssel aktiv.")
