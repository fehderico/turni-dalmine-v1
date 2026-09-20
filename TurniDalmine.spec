from __future__ import annotations

import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = os.path.abspath(SPECPATH)
datas = [(os.path.join(project_root, "app.py"), ".")]
binaries = []
hiddenimports = collect_submodules("turni")

for package in ("streamlit", "ortools", "reportlab", "openpyxl", "altair"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

analysis = Analysis(
    [os.path.join(project_root, "desktop_launcher.py")],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="AVVIA TURNI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Turni Dalmine",
)

if sys.platform == "darwin":
    app = BUNDLE(
        bundle,
        name="AVVIA TURNI.app",
        icon=None,
        bundle_identifier="it.dalmine.turni",
        info_plist={
            "CFBundleDisplayName": "Turni Dalmine",
            "NSHighResolutionCapable": True,
        },
    )
