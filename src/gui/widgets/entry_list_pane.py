"""Middle pane: search field, entry list, and empty-state label."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.models import Entry


class EntryListPane(QWidget):
    """Fixed-width pane containing a search field and a scrollable entry list.

    When the list is empty after a set_entries() call the widget switches to an
    empty-state label whose message can be customised via set_empty_message().

    Signals
    -------
    entry_selected(int)
        Emitted with the entry's database id when the user clicks a list item
        or when select_entry() programmatically sets the current item.
    search_changed(str)
        Emitted on every keystroke in the search field.
    """

    entry_selected = Signal(int)
    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the search field, list widget, and empty-state stack."""
        super().__init__(parent)
        self.setObjectName("entryListPane")
        self.setFixedWidth(340)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Lay out the search field on top of a stacked list/empty-label pair."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Suchen…")
        self._search_edit.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self._search_edit)

        # Stack: index 0 = list, index 1 = empty-state label.
        self._stack = QStackedWidget()

        self._list_widget = QListWidget()
        self._list_widget.setSpacing(1)
        self._list_widget.currentItemChanged.connect(self._on_item_changed)
        self._stack.addWidget(self._list_widget)

        self._empty_label = QLabel("Keine Einträge gefunden")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._stack.addWidget(self._empty_label)

        layout.addWidget(self._stack, 1)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def set_entries(self, entries: list[Entry]) -> None:
        """Replace the list contents with entries.

        Signals are blocked during the rebuild so intermediate currentItemChanged
        emissions don't fire while the list is in a partial state.
        """
        self._list_widget.blockSignals(True)
        self._list_widget.clear()
        for entry in entries:
            item = QListWidgetItem(self._list_widget)
            item.setData(Qt.UserRole, entry.id)
            item.setSizeHint(QSize(0, 52))
            self._list_widget.setItemWidget(item, self._make_item_widget(entry))
        self._list_widget.blockSignals(False)

        if entries:
            self._stack.setCurrentWidget(self._list_widget)
        else:
            self._stack.setCurrentWidget(self._empty_label)

    def set_empty_message(self, text: str) -> None:
        """Set the message shown when the list is empty."""
        self._empty_label.setText(text)

    def select_entry(self, entry_id: int) -> bool:
        """Programmatically select the item with entry_id.

        Returns True if the item was found and selected, False otherwise.
        When True, currentItemChanged fires which will emit entry_selected.
        """
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item and item.data(Qt.UserRole) == entry_id:
                self._list_widget.setCurrentItem(item)
                return True
        return False

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _make_item_widget(entry: Entry) -> QWidget:
        """Build the two-line title + username widget for a list item."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)

        title_lbl = QLabel(entry.title)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(entry.username or "")
        sub_lbl.setObjectName("entrySubtitle")
        layout.addWidget(sub_lbl)

        return container

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    def _on_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        """Forward the selected entry's id via entry_selected."""
        if current is None:
            return
        entry_id: int | None = current.data(Qt.UserRole)
        if entry_id is not None:
            self.entry_selected.emit(entry_id)
