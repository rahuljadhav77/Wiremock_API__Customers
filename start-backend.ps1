$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot "backend"

Set-Location $backendRoot

python --version 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "Python 3 is required. Install from https://www.python.org/downloads/ and retry."
}

Write-Host "Installing Python dependencies..."
python -m pip install -q -r requirements.txt

Write-Host "Starting customer API (Excel/CSV) on http://127.0.0.1:5001 ..."
python app.py
