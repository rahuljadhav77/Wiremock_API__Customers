$ErrorActionPreference = "Stop"

$procs = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "rates-api" }
if ($procs.Count -gt 0) {
  Write-Host "Stopping rates API..."
  $procs | Stop-Process -Force
  Start-Sleep -Seconds 1
  Write-Host "Rates API stopped."
} else {
  Write-Host "Rates API is not running."
}
