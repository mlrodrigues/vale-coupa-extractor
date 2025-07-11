# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

datas = []
binaries = []
datas += collect_data_files('playwright')
binaries += collect_dynamic_libs('playwright')


a = Analysis(
    ['main_refactored.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['playwright', 'playwright.sync_api', 'playwright._impl', 'greenlet', 'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'csv', 'logging', 'datetime', 're', 'time', 'os', 'typing', 'abc', 'dataclasses', 'enum'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ValeCoupaCrawler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
