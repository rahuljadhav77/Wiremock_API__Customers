$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$jarPath = Join-Path $projectRoot "tools\wiremock-standalone-3.9.1.jar"
$wiremockRoot = Join-Path $projectRoot "wiremock"
$logDir = Join-Path $projectRoot "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir "wiremock.log"

if (-not (Test-Path $jarPath)) {
  throw "WireMock jar not found at $jarPath"
}

Write-Host "Starting WireMock on http://localhost:8080 ..."
java -jar $jarPath --port 8080 --root-dir $wiremockRoot --verbose --global-response-templating 2>&1 |
  Tee-Object -FilePath $logPath -Append
