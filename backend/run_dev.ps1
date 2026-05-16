# Arranque local con el intérprete del venv del backend (Windows PowerShell).
# Uso: desde esta carpeta: .\run_dev.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".\.venv\Scripts\uvicorn.exe")) {
  Write-Host "Falta backend/.venv. Crear con: python -m venv .venv" -ForegroundColor Yellow
  Write-Host "Luego: .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
  exit 1
}
& .\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
