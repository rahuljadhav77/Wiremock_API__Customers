$ErrorActionPreference = "Stop"

$procs = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "loan-api" }
if ($procs.Count -gt 0) {
  Write-Host "Stopping loans API..."
  $procs | Stop-Process -Force
  Start-Sleep -Seconds 1
  Write-Host "Loans API stopped."
} else {
  Write-Host "Loans API is not running."
}
