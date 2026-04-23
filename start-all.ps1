$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot "backend"

python --version 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "Python 3 is required. Install from https://www.python.org/downloads/ and retry."
}

Push-Location $backendRoot
try {
  Write-Host "Installing Python dependencies..."
  python -m pip install -q -r requirements.txt
} finally {
  Pop-Location
}

Write-Host "Starting backend (Excel/CSV) on http://127.0.0.1:5001 (minimized window)..."
$backendScript = Join-Path $backendRoot "app.py"
$backendProc = Start-Process -FilePath "python" `
  -ArgumentList @($backendScript) `
  -WorkingDirectory $backendRoot `
  -PassThru `
  -WindowStyle Minimized

$healthy = $false
for ($i = 0; $i -lt 40; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5001/health" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) {
      $healthy = $true
      break
    }
  } catch {
    Start-Sleep -Seconds 1
  }
}

if (-not $healthy) {
  try { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
  throw "Backend did not respond on http://127.0.0.1:5001/health. Check Python errors in the minimized window or run .\start-backend.ps1 in a visible terminal."
}

Write-Host "Backend OK. Starting WireMock on http://127.0.0.1:8080 (CTRL+C stops WireMock only; use .\stop-all.ps1 to stop both)."
& (Join-Path $projectRoot "start-wiremock.ps1")
