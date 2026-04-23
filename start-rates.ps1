$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ratesRoot = Join-Path $projectRoot "rates-api"

python --version 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "Python 3 is required. Install from https://www.python.org/downloads/"
}

Push-Location $ratesRoot
try {
  Write-Host "Installing rates API dependencies..."
  python -m pip install -q -r requirements.txt
} finally {
  Pop-Location
}

Write-Host "Starting rates API on http://127.0.0.1:5002 (minimized window)..."
$ratesScript = Join-Path $ratesRoot "app.py"
$ratesProc = Start-Process -FilePath "python" `
  -ArgumentList @($ratesScript) `
  -WorkingDirectory $ratesRoot `
  -PassThru `
  -WindowStyle Minimized

$healthy = $false
for ($i = 0; $i -lt 40; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5002/health" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) {
      $healthy = $true
      break
    }
  } catch {
    Start-Sleep -Seconds 1
  }
}

if (-not $healthy) {
  try { Stop-Process -Id $ratesProc.Id -Force -ErrorAction SilentlyContinue } catch {}
  throw "Rates API did not respond on http://127.0.0.1:5002/health. Check Python errors in the minimized window or run it in a visible terminal."
}

Write-Host "Rates API is healthy and running on port 5002."
Write-Host "Use .\stop-rates.ps1 to stop it."
