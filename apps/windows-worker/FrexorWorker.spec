# Build on Windows with: pyinstaller FrexorWorker.spec
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("googleapiclient")

a = Analysis(
    ["worker_launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=datas + [("frexor_ui_map.example.toml", ".")],
    hiddenimports=[
        "PySide6.QtCore", "pywinauto", "pythoncom", "pywintypes",
        "openpyxl", "httpx", "pypdf", "psutil",
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
    [],
    name="Frexor Worker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    exclude_binaries=True,
    argv_emulation=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="Frexor Worker",
)
