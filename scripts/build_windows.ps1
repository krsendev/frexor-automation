$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -m venv .venv
}

& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -e ".[worker,build]"
if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}
if (Test-Path "dist\Frexor Assessment Automation") {
    Remove-Item "dist\Frexor Assessment Automation" -Recurse -Force
}
if (Test-Path "dist\Frexor Assessment Automation.exe") {
    Remove-Item "dist\Frexor Assessment Automation.exe" -Force
}
& .venv\Scripts\python.exe -m PyInstaller FrexorAutomation.spec --noconfirm --clean

Write-Host "Build selesai: dist\Frexor Assessment Automation\Frexor Assessment Automation.exe"
