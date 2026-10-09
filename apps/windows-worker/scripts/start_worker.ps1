param([string]$WorkerDirectory = "")

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($WorkerDirectory)) {
    $WorkerDirectory = Join-Path $ProjectRoot "dist\Frexor Worker"
}
$WorkerDirectory = [System.IO.Path]::GetFullPath($WorkerDirectory)
$Executable = Join-Path $WorkerDirectory "Frexor Worker.exe"
$Config = Join-Path $WorkerDirectory "config.toml"
if (-not (Test-Path $Executable)) { throw "Executable worker tidak ditemukan: $Executable" }
if (-not (Test-Path $Config)) { throw "Konfigurasi worker tidak ditemukan: $Config" }
Start-Process -FilePath $Executable -ArgumentList "--config `"$Config`" worker" -WorkingDirectory $WorkerDirectory
Write-Host "Frexor Worker dijalankan."
