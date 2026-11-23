# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Wrye BashMon NG.

Run from the repo root:  pyinstaller build.spec

Wrye Bash's 'bash' package is imported dynamically, so PyInstaller cannot
see it. This spec boots it headless at build time and passes every 'bash'
module that got loaded as a hidden import; PyInstaller then follows their
imports (stdlib and third-party) as usual. wx and the GUI are excluded.
"""
import os
import sys

base_dir = os.path.dirname(os.path.abspath(SPEC))
mopy = os.path.join(base_dir, 'wrye-bash', 'Mopy')
sys.path.insert(0, base_dir)

from bashmon_ng import wb_boot
wb_boot.boot(base_dir) # any folder works - only the game object is built
from bashmon_ng import saves  # noqa: F401
bash_modules = sorted(m for m in sys.modules
                      if m == 'bash' or m.startswith('bash.'))

a = Analysis(
    [os.path.join('bashmon_ng', '__main__.py')],
    pathex=[base_dir, mopy],
    binaries=[],
    datas=[(os.path.join('bashmon_ng', 'icons'),
            os.path.join('bashmon_ng', 'icons'))],
    hiddenimports=bash_modules + ['pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['wx', 'bash.basher', 'bash.balt', 'bash.gui'],
    noarchive=False,
)

pyz = PYZ(a.pure)

# Onefile build: one self-contained dist\bashmon.exe. It runs as two
# processes (PyInstaller's unpacker plus the app); that is expected.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='bashmon',  # same exe name as the original, for existing launchers
    icon=os.path.join('bashmon_ng', 'icons', 'bash_icons_blue.ico'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
