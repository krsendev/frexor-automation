param(
    [string]$WorkerDirectory = "",
    [string]$TaskName = "Frexor Automation Worker"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($WorkerDirectory)) {
    $WorkerDirectory = Join-Path $ProjectRoot "dist\Frexor Worker"
}
$WorkerDirectory = [System.IO.Path]::GetFullPath($WorkerDirectory)
$Executable = Join-Path $WorkerDirectory "Frexor Worker.exe"
$Config = Join-Path $WorkerDirectory "config.toml"

if (-not (Test-Path $Executable)) {
    throw "Executable worker tidak ditemukan: $Executable"
}
if (-not (Test-Path $Config)) {
    throw "Konfigurasi worker tidak ditemukan: $Config"
}

$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Arguments = "--config `"$Config`" worker"
$Action = New-ScheduledTaskAction `
    -Execute $Executable `
    -Argument $Arguments `
    -WorkingDirectory $WorkerDirectory
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
$Principal = New-ScheduledTaskPrincipal `
    -UserId $CurrentUser `
    -LogonType Interactive `
    -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

$InstalledWithTaskScheduler = $false
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "Frexor API worker. Membutuhkan sesi desktop user aktif dan tidak terkunci." `
        -Force `
        -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $TaskName
    $InstalledWithTaskScheduler = $true
    Write-Host "Task '$TaskName' terpasang dan dijalankan untuk user $CurrentUser."
}
catch {
    Write-Warning "Task Scheduler tidak kompatibel pada VM ini: $($_.Exception.Message)"
    Write-Host "Memasang fallback Startup shortcut untuk user $CurrentUser..."

    $StartupDirectory = [Environment]::GetFolderPath("Startup")
    $ShortcutPath = Join-Path $StartupDirectory "Frexor Automation Worker.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $Executable
    $Shortcut.Arguments = $Arguments
    $Shortcut.WorkingDirectory = $WorkerDirectory
    $Shortcut.Description = "Frexor API background worker"
    $Shortcut.Save()

    Start-Process `
        -FilePath $Executable `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkerDirectory
    Write-Host "Startup shortcut terpasang: $ShortcutPath"
}

if ($InstalledWithTaskScheduler) {
    Write-Host "Mode startup: Task Scheduler"
}
else {
    Write-Host "Mode startup: Windows Startup folder"
}
Write-Host "Launcher akan mencoba ulang setelah 60 detik jika worker berhenti karena error."
Write-Host "Log worker: $WorkerDirectory\logs\automation.log"
