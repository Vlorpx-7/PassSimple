"""Left navigation sidebar: app header, vault section, action buttons."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Signal, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_ASSETS_DIR = Path(__file__).parent.parent.parent.parent / "assets"


class NavSidebar(QWidget):
    """Fixed-width navigation sidebar with radio-style vault filter buttons.

    Signals
    -------
    nav_changed(str)
        Emitted with one of: "all", "favorites", "import", "settings".
        "all" and "favorites" are stateful nav items (checkable, mutually exclusive).
        "import" and "settings" are one-shot actions with no persistent state.
    """

    nav_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the sidebar layout and select 'Alle Einträge' by default."""
        super().__init__(parent)
        self.setObjectName("navSidebar")
        self.setFixedWidth(190)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        # Required so QSS background-color applies to a plain QWidget.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui()
        self._btn_all.setChecked(True)

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _init_ui(self) -> None:
        """Lay out the header, section label, nav items, spacer, and footer."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(0)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_section_label("Tresor"))
        layout.addWidget(self._make_nav_btn("Alle Einträge", "all", checkable=True))
        layout.addWidget(self._make_nav_btn("Favoriten", "favorites", checkable=True))
        layout.addWidget(self._make_nav_btn("Import", "import", checkable=False))
        layout.addStretch()
        settings_btn = self._make_nav_btn("Einstellungen", "settings", checkable=False)
        settings_btn.setToolTip("Einstellungen öffnen")
        layout.addWidget(settings_btn)

    def _build_header(self) -> QHBoxLayout:
        """App icon (32×32) + bold 'PassSimple' title label."""
        row = QHBoxLayout()
        row.setContentsMargins(12, 14, 12, 10)
        row.setSpacing(8)

        icon_lbl = QLabel()
        icon_path = _ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            pixmap = QIcon(str(icon_path)).pixmap(QSize(32, 32))
            icon_lbl.setPixmap(pixmap)
        row.addWidget(icon_lbl)

        title_lbl = QLabel("PassSimple")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title_lbl.setFont(font)
        row.addWidget(title_lbl, 1)
        return row

    @staticmethod
    def _build_section_label(text: str) -> QLabel:
        """Dimmed uppercase-style section header."""
        lbl = QLabel(text.upper())
        lbl.setObjectName("navSectionHeader")
        return lbl

    def _make_nav_btn(self, label: str, value: str, *, checkable: bool) -> QPushButton:
        """Create a nav button and wire it to nav_changed."""
        btn = QPushButton(label)
        btn.setObjectName("navItem")
        btn.setCheckable(checkable)
        if checkable:
            btn.setAutoExclusive(True)
            # Store reference so __init__ can call setChecked on it.
            if value == "all":
                self._btn_all = btn
            elif value == "favorites":
                self._btn_favorites = btn
            btn.clicked.connect(lambda _checked, v=value: self.nav_changed.emit(v))
        else:
            btn.clicked.connect(lambda: self.nav_changed.emit(value))
        return btn
