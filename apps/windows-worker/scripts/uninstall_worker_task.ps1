param(
    [string]$TaskName = "Frexor Automation Worker"
)

$ErrorActionPreference = "Stop"
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $Task) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Task '$TaskName' sudah dihentikan dan dihapus."
}

$StartupDirectory = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDirectory "Frexor Automation Worker.lnk"
if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Startup shortcut sudah dihapus: $ShortcutPath"
}

if ($null -eq $Task -and -not (Test-Path $ShortcutPath)) {
    Write-Host "Scheduled task dan Startup shortcut sudah tidak terpasang."
}
