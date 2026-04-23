$ErrorActionPreference = "SilentlyContinue"

$conns = Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
  Write-Host "No process listening on port 5001."
  exit 0
}

$procIds = $conns.OwningProcess | Select-Object -Unique
foreach ($procId in $procIds) {
  Stop-Process -Id $procId -Force
  Write-Host "Stopped backend process $procId (port 5001)."
}
