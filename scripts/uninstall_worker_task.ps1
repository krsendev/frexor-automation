param(
    [string]$TaskName = "Frexor Automation Worker"
)

$ErrorActionPreference = "Stop"
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $Task) {
    Write-Host "Task '$TaskName' tidak ditemukan."
    exit 0
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Task '$TaskName' sudah dihentikan dan dihapus."
