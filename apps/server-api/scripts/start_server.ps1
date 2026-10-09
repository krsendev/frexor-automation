param([string]$ServerDirectory = "")

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ServerDirectory)) {
    $ServerDirectory = Join-Path $ProjectRoot "dist\Frexor Server"
}
$Executable = Join-Path ([System.IO.Path]::GetFullPath($ServerDirectory)) "Frexor Server.exe"
if (-not (Test-Path $Executable)) { throw "Executable server tidak ditemukan: $Executable" }
Start-Process -FilePath $Executable -WorkingDirectory (Split-Path $Executable -Parent)
Write-Host "Frexor Server dijalankan."
