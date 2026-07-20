# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for 3D Car Rush.

Build with:   pyinstaller --noconfirm car_rush.spec
Output:       dist/3D Car Rush.exe   (single-file, windowed)
"""

import os
import OpenGL

# PyOpenGL loads freeglut/gle from OpenGL/DLLS at runtime -- bundle them so the
# frozen exe can create its GLUT window on machines without PyOpenGL installed.
_dlls_dir = os.path.join(os.path.dirname(OpenGL.__file__), "DLLS")
opengl_binaries = [
    (os.path.join(_dlls_dir, f), os.path.join("OpenGL", "DLLS"))
    for f in os.listdir(_dlls_dir) if f.lower().endswith(".dll")
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=opengl_binaries,
    datas=[("assets/logo.png", "assets")],   # menu logo (loaded at runtime)
    hiddenimports=[
        "OpenGL.platform.win32",
        "OpenGL.arrays.ctypesarrays",
        "OpenGL.arrays.numpymodule",
        "OpenGL.arrays.lists",
        "OpenGL.arrays.numbers",
        "OpenGL.arrays.strings",
        "OpenGL.arrays.ctypespointers",
        "OpenGL.arrays.nones",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="3D Car Rush",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,          # windowed app -- no console window
    icon="assets/icon.ico",
)
