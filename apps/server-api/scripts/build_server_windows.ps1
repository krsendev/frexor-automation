$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -m venv .venv
}

& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -e ".[build,test]"
& .venv\Scripts\python.exe -m PyInstaller FrexorServer.spec --noconfirm --clean

$OutputDirectory = Join-Path $ProjectRoot "dist\Frexor Server"
Copy-Item ".env.windows.example" (Join-Path $OutputDirectory ".env.example") -Force

Write-Host "Build selesai: $OutputDirectory\Frexor Server.exe"
Write-Host "Buat file .env pada folder output sebelum menjalankan server."
