$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$uiRoot = Join-Path $projectRoot "monitor-ui"

Set-Location $uiRoot

python --version 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "Python 3 is required."
}

Write-Host "Installing monitor-ui dependencies..."
python -m pip install -q -r requirements.txt

$port = if ($env:MONITOR_PORT) { $env:MONITOR_PORT } else { "5055" }
Write-Host "Starting monitor UI on http://127.0.0.1:$port ..."
$env:MONITOR_PORT = $port
python app.py
