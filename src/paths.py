"""Runtime resource-path resolver — works in dev mode and inside a PyInstaller bundle."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Return the absolute path to a bundled resource file.

    In dev: resolves relative to the project root (one level above src/).
    In a PyInstaller one-file bundle: resolves relative to sys._MEIPASS,
    the temporary directory where bundled data files are extracted at runtime.
    """
    if hasattr(sys, "_MEIPASS"):
        # Running inside a PyInstaller bundle — data lives in the extraction dir.
        return Path(sys._MEIPASS) / relative
    # __file__ is src/paths.py → .parent = src/ → .parent.parent = project root
    return Path(__file__).parent.parent / relative
