param(
    [string]$ServerDirectory = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ServerDirectory)) {
    $ServerDirectory = Join-Path $ProjectRoot "dist\Frexor Server"
}
$ServerDirectory = [System.IO.Path]::GetFullPath($ServerDirectory)
$Executable = Join-Path $ServerDirectory "Frexor Server.exe"
$EnvironmentFile = Join-Path $ServerDirectory ".env"

if (-not (Test-Path $Executable)) { throw "Executable server tidak ditemukan: $Executable" }
if (-not (Test-Path $EnvironmentFile)) { throw "File environment tidak ditemukan: $EnvironmentFile" }

$StartupDirectory = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDirectory "Frexor Server.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Executable
$Shortcut.WorkingDirectory = $ServerDirectory
$Shortcut.Description = "Frexor Automation API"
$Shortcut.Save()

Start-Process -FilePath $Executable -WorkingDirectory $ServerDirectory
Write-Host "Server dijalankan dan Startup shortcut dipasang: $ShortcutPath"
Write-Host "Log: $ServerDirectory\logs\server.log"
