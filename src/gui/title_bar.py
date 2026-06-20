"""Module-level theme cache and Windows DWM title-bar styling for all top-level windows.

Usage pattern
-------------
1. At app startup, call set_current_theme() with the persisted theme value.
2. Whenever the user changes the theme, call set_current_theme() again.
3. In every QDialog/QMainWindow.showEvent(), call apply_title_bar(self).

This avoids passing a theme argument through the call stack and gives every
dialog consistent title-bar colours with a single import.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

_current_theme: str = "dark"


def set_current_theme(theme: str) -> None:
    """Update the module-level theme cache.

    Call this at startup (from app.py) and whenever the user switches themes
    (from MainWindow.apply_theme).  All subsequent apply_title_bar() calls will
    pick up the new value automatically.
    """
    global _current_theme
    _current_theme = theme


def apply_title_bar(widget: QWidget) -> None:
    """Apply Windows 11 DWM title-bar colours to any top-level Qt window.

    Reads the current theme from the module-level cache set by set_current_theme().

    dark  → immersive dark mode on;  caption #1e1e2e (BGR 0x2E1E1E),
                                      text    #cdd6f4 (BGR 0xF4D6CD).
    light → immersive dark mode off; caption #eff1f5 (BGR 0xF5F1EF),
                                      text    #4c4f69 (BGR 0x694F4C).

    On non-Windows platforms ctypes.windll raises AttributeError — silently
    ignored so cross-platform imports work.  DWMWA_CAPTION_COLOR /
    DWMWA_TEXT_COLOR require Windows 11 Build 22000+; older builds silently
    ignore those two attribute calls.
    """
    try:
        import ctypes
        hwnd = int(widget.winId())

        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        dark_value = ctypes.c_int(0 if _current_theme == "light" else 1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_value),
            ctypes.sizeof(dark_value),
        )

        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36
        if _current_theme == "light":
            caption_color = ctypes.c_uint(0xF5F1EF)  # #eff1f5 → BGR
            text_color    = ctypes.c_uint(0x694F4C)   # #4c4f69 → BGR
        else:
            caption_color = ctypes.c_uint(0x2E1E1E)   # #1e1e2e → BGR
            text_color    = ctypes.c_uint(0xF4D6CD)   # #cdd6f4 → BGR
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_CAPTION_COLOR,
            ctypes.byref(caption_color), ctypes.sizeof(caption_color),
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_TEXT_COLOR,
            ctypes.byref(text_color), ctypes.sizeof(text_color),
        )

        DWMWA_BORDER_COLOR = 34
        if _current_theme == "light":
            border_color = ctypes.c_uint(0xCCC0BC)  # #bcc0cc → BGR
        else:
            border_color = ctypes.c_uint(0x2E1E1E)  # #1e1e2e → BGR
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR,
            ctypes.byref(border_color), ctypes.sizeof(border_color),
        )
    except Exception:
        pass
