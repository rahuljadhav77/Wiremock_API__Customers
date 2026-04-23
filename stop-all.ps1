$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $projectRoot "stop-wiremock.ps1")
& (Join-Path $projectRoot "stop-backend.ps1")

Write-Host "Done."
