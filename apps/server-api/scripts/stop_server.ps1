$ErrorActionPreference = "Stop"
$Processes = Get-Process -Name "Frexor Server" -ErrorAction SilentlyContinue
if ($null -eq $Processes) {
    Write-Host "Frexor Server tidak sedang berjalan."
    exit 0
}
$Processes | Stop-Process -Force
Write-Host "Frexor Server sudah dihentikan."
