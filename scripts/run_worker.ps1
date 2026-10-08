$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Config = Join-Path $ProjectRoot "config.toml"

if (-not (Test-Path $Python)) {
    throw "Virtual environment tidak ditemukan: $Python"
}

if (-not (Test-Path $Config)) {
    throw "Konfigurasi worker tidak ditemukan: $Config"
}

Set-Location $ProjectRoot
& $Python -m frexor_automation.cli --config $Config worker
