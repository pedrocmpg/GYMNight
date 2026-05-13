# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Arquivos de dados a incluir
added_files = [
    ('docs/*.md', 'docs'),
    ('muscle_usage_map.md', '.'),
    ('README.md', '.'),
    ('COMO_EXECUTAR.md', '.'),
    ('assets/images', 'assets/images'),
    ('.env', '.'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'sqlalchemy',
        'pydantic',
        'dotenv',
        'numpy',
        'matplotlib',
        'qtawesome',
        'google.genai',
        'loguru',
        'pillow',
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

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GYMNight',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False = sem janela de console (GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icons/gymnight.ico',  # Descomente se tiver um ícone
)
