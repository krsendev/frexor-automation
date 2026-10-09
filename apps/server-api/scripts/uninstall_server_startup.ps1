$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "stop_server.ps1")
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Startup")) "Frexor Server.lnk"
if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Startup shortcut dihapus: $ShortcutPath"
}
