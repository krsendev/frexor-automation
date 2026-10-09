$ErrorActionPreference = "Stop"
$Processes = Get-Process -Name "Frexor Worker" -ErrorAction SilentlyContinue
if ($null -eq $Processes) {
    Write-Host "Frexor Worker tidak sedang berjalan."
    exit 0
}
$Processes | Stop-Process -Force
Write-Host "Frexor Worker sudah dihentikan."
