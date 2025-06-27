# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Arquivos e pastas a serem incluídos
added_files = [
    ['requirements.txt', '.'], ('C:/Users/Ryzen/AppData/Local/ms-playwright', 'ms-playwright')
]

# Configuração para Windows
a = Analysis(
    ['main_refactored.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'playwright.sync_api',
        'playwright.async_api', 
        'openpyxl',
        'pandas',
        'requests',
        'tkinter',
        'tkinter.ttk',
        'csv',
        'datetime',
        'pathlib',
        'hashlib',
        'urllib.parse',
        'threading',
        'logging',
        're',
        'time',
        'os',
        'sys',
        'json',
        'shutil',
        'subprocess',
        'platform'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Configuração para executável
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Vale_Coupa_Crawler_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False para aplicação GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Adicione ícone aqui se tiver
    version_file=None,
)
