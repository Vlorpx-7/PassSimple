# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PassSimple — one-file Windows build.

Run from the project root:
    pyinstaller build/passsimple.spec --distpath build/dist --workpath build/build --noconfirm
"""

import os

# SPECPATH is injected by PyInstaller = directory containing this spec file.
# From build/ we go up one level to get the project root.
project_root = os.path.normpath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(project_root, "src", "app.py")],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, "assets", "icon.ico"), "assets"),
        (os.path.join(project_root, "src", "gui", "styles_dark.qss"), os.path.join("src", "gui")),
        (os.path.join(project_root, "src", "gui", "styles_light.qss"), os.path.join("src", "gui")),
    ],
    hiddenimports=[
        # pywin32 — DPAPI and Windows APIs
        "win32crypt",
        "win32api",
        "win32con",
        "win32security",
        "pywintypes",
        "win32timezone",
        # keyboard library — Windows hook backend is selected at runtime, not statically
        "keyboard",
        "keyboard._winkeyboard",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "requests",
        "urllib3",
        "httpx",
        "tkinter",
        "_tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PassSimple",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(project_root, "assets", "icon.ico"),
    version=os.path.join(SPECPATH, "version_info.txt"),
    uac_admin=False,
)
