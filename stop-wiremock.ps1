$ErrorActionPreference = "SilentlyContinue"

$wiremockProcesses = Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like "*wiremock-standalone-3.9.1.jar*" }

if (-not $wiremockProcesses) {
  Write-Host "No running WireMock process found."
  exit 0
}

foreach ($p in $wiremockProcesses) {
  Stop-Process -Id $p.ProcessId -Force
  Write-Host "Stopped WireMock process $($p.ProcessId)"
}
