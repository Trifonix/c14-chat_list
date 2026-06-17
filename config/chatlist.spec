# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))
from load_version import load_version

__version__ = load_version()

_project_root = Path(SPECPATH).parent
_main_script = str(_project_root / "main.py")
_src_path = str(_project_root / "src")
_env_file = _project_root / "config" / ".env"
_datas = [(str(_env_file), "config")] if _env_file.exists() else []

block_cipher = None

excludes = [
    'PySide6',
    'PySide2',
    'PyQt5',
    'matplotlib',
    'numpy',
    'IPython',
    'jupyter',
    'notebook',
    'tkinter',
]

a = Analysis(
    [_main_script],
    pathex=[_src_path],
    binaries=[],
    datas=_datas,
    hiddenimports=['dotenv', 'httpx', 'certifi'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f'chatlist-{__version__}',
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
