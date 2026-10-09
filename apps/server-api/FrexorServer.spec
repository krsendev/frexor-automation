# Build on Windows with: pyinstaller FrexorServer.spec
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
for package in ("fastapi", "starlette", "pydantic", "uvicorn", "multipart"):
    hiddenimports += collect_submodules(package)
hiddenimports += ["frexor_api.main"]

a = Analysis(
    ["server_launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
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
    name="Frexor Server",
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
    name="Frexor Server",
)
