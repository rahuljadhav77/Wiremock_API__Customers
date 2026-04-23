$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$loansRoot = Join-Path $projectRoot "loan-api"

python --version 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "Python 3 is required. Install from https://www.python.org/downloads/"
}

Push-Location $loansRoot
try {
  Write-Host "Installing loans API dependencies..."
  python -m pip install -q -r requirements.txt
} finally {
  Pop-Location
}

Write-Host "Starting loans API on http://127.0.0.1:5003 (minimized window)..."
$loansScript = Join-Path $loansRoot "app.py"
$loansProc = Start-Process -FilePath "python" `
  -ArgumentList @($loansScript) `
  -WorkingDirectory $loansRoot `
  -PassThru `
  -WindowStyle Minimized

$healthy = $false
for ($i = 0; $i -lt 40; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5003/health" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) {
      $healthy = $true
      break
    }
  } catch {
    Start-Sleep -Seconds 1
  }
}

if (-not $healthy) {
  try { Stop-Process -Id $loansProc.Id -Force -ErrorAction SilentlyContinue } catch {}
  throw "Loans API did not respond on http://127.0.0.1:5003/health. Check Python errors in the minimized window or run it in a visible terminal."
}

Write-Host "Loans API is healthy and running on port 5003."
Write-Host "Use .\stop-loans.ps1 to stop it."
