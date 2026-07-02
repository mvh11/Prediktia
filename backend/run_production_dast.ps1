# Arranque local con APP_ENV=production (validacion DAST / hardening).
# Uso: desde backend/  .\run_production_dast.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".\.venv\Scripts\uvicorn.exe")) {
  Write-Host "Falta backend/.venv" -ForegroundColor Yellow
  exit 1
}
$env:APP_ENV = "production"
if (-not $env:FRONTEND_URL) {
  $env:FRONTEND_URL = "http://localhost:3000"
}
Write-Host "APP_ENV=$env:APP_ENV FRONTEND_URL=$env:FRONTEND_URL"
& .\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --no-server-header
