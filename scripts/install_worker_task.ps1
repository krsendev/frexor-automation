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

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Frexor API worker. Membutuhkan sesi desktop user aktif dan tidak terkunci." `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Write-Host "Task '$TaskName' terpasang dan dijalankan untuk user $CurrentUser."
Write-Host "Launcher akan mencoba ulang setelah 60 detik jika worker berhenti karena error."
Write-Host "Log worker: $WorkerDirectory\logs\automation.log"
