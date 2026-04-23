$ErrorActionPreference = "SilentlyContinue"

$port = if ($env:MONITOR_PORT) { [int]$env:MONITOR_PORT } else { 5055 }

$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
  Write-Host "No process listening on port $port."
  exit 0
}

$procIds = $conns.OwningProcess | Select-Object -Unique
foreach ($procId in $procIds) {
  Stop-Process -Id $procId -Force
  Write-Host "Stopped monitor UI process $procId (port $port)."
}
