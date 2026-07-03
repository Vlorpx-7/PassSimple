"""Splash screen shown during vault bootstrap before the main window appears."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen

from src.i18n import tr
from src.paths import resource_path

_W, _H = 400, 300


def create_splash() -> QSplashScreen:
    """Build and return a styled QSplashScreen ready to be shown.

    The splash is composited entirely from a single QPixmap so that Qt renders
    it as one opaque surface — no child widgets, no layout, no flickering.
    """
    pixmap = _build_pixmap()
    splash = QSplashScreen(
        pixmap,
        Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen,
    )
    splash.setEnabled(False)  # clicks pass through to the desktop
    return splash


def _build_pixmap() -> QPixmap:
    """Compose the splash graphic: background + icon + title + subtitle."""
    pixmap = QPixmap(_W, _H)
    pixmap.fill(QColor("#1e1e2e"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    icon_top = _draw_icon(painter)
    title_bottom = _draw_title(painter, icon_top)
    _draw_subtitle(painter, title_bottom)

    painter.end()
    return pixmap


def _draw_icon(painter: QPainter) -> int:
    """Draw the 96×96 app icon centred horizontally near the top. Returns the icon bottom y."""
    icon_size = 96
    icon_path = resource_path("assets/icon.ico")
    if icon_path.exists():
        icon_pixmap = QIcon(str(icon_path)).pixmap(icon_size, icon_size)
    else:
        icon_pixmap = QPixmap(icon_size, icon_size)
        icon_pixmap.fill(QColor("#313244"))

    icon_x = (_W - icon_size) // 2
    icon_y = 60
    painter.drawPixmap(icon_x, icon_y, icon_pixmap)
    return icon_y + icon_size


def _draw_title(painter: QPainter, icon_bottom: int) -> int:
    """Draw 'PassSimple' in 22pt bold below the icon. Returns the text bottom y."""
    font = QFont("Segoe UI Variable", 22)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#cdd6f4"))

    top = icon_bottom + 18
    painter.drawText(0, top, _W, 40, Qt.AlignmentFlag.AlignHCenter, "PassSimple")
    return top + 40


def _draw_subtitle(painter: QPainter, title_bottom: int) -> None:
    """Draw 'Wird geladen…' in 11pt below the title."""
    font = QFont("Segoe UI Variable", 11)
    painter.setFont(font)
    painter.setPen(QColor("#a6adc8"))
    painter.drawText(0, title_bottom + 6, _W, 24, Qt.AlignmentFlag.AlignHCenter, tr("app.loading"))
