$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -m venv .venv
}

& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -e ".[build]"
& .venv\Scripts\python.exe -m PyInstaller FrexorWorker.spec --noconfirm --clean

$OutputDirectory = Join-Path $ProjectRoot "dist\Frexor Worker"
Copy-Item "config.example.toml" (Join-Path $OutputDirectory "config.example.toml") -Force
Copy-Item "frexor_ui_map.example.toml" (Join-Path $OutputDirectory "frexor_ui_map.example.toml") -Force

Write-Host "Build selesai: $OutputDirectory\Frexor Worker.exe"
Write-Host "Salin config.toml dan frexor_ui_map.toml yang sudah valid ke folder tersebut."
