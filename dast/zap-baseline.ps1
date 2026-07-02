# OWASP ZAP baseline scan — Prediktia API
# Imagen oficial: https://www.zaproxy.org/docs/docker/baseline-scan/
# Requisitos: Docker Desktop (daemon activo), backend en http://127.0.0.1:8000
# Uso (desde la raíz del repo):
#   .\dast\zap-baseline.ps1
#   .\dast\zap-baseline.ps1 -TargetUrl "http://host.docker.internal:8000"

param(
    [string]$TargetUrl = "http://host.docker.internal:8000",
    [string]$ZapImage = "ghcr.io/zaproxy/zaproxy:stable",
    [string]$ReportHtml = "dast/zap-report.html",
    [string]$ReportJson = "dast/zap-report.json"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "Comprobando objetivo local (127.0.0.1:8000) ..."
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 10
    if ($health.StatusCode -ne 200) {
        throw "Health check devolvio $($health.StatusCode)"
    }
} catch {
    Write-Error "El backend no responde en http://127.0.0.1:8000. Arranca uvicorn antes del escaneo."
    exit 1
}

$WorkDir = Join-Path $RepoRoot "dast"
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

$HtmlName = Split-Path -Leaf $ReportHtml
$JsonName = Split-Path -Leaf $ReportJson

Write-Host "Imagen ZAP: $ZapImage"
Write-Host "Objetivo del contenedor: $TargetUrl"
Write-Host "Ejecutando OWASP ZAP baseline (puede tardar varios minutos)..."

# -t: TTY requerido por la imagen oficial
# Montar dast/ en /zap/wrk: los informes usan nombre de archivo relativo (cwd del contenedor)
docker run --rm `
    -v "${WorkDir}:/zap/wrk:rw" `
    -t $ZapImage `
    zap-baseline.py `
    -t $TargetUrl `
    -r $HtmlName `
    -J $JsonName `
    -I `
    -s `
    --autooff

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "Reportes generados:"
Write-Host "  HTML: $(Join-Path $WorkDir $HtmlName)"
Write-Host "  JSON: $(Join-Path $WorkDir $JsonName)"

switch ($exitCode) {
    0 { Write-Host "ZAP baseline: OK (sin FAIL ni WARN significativos)." -ForegroundColor Green }
    1 { Write-Host "ZAP baseline: FAIL — al menos una alerta critica. Revisa el informe HTML." -ForegroundColor Red }
    2 { Write-Host "ZAP baseline: WARN — alertas de advertencia detectadas. Revisa el informe HTML." -ForegroundColor Yellow }
    default { Write-Host "ZAP baseline: error de ejecucion (codigo $exitCode)." -ForegroundColor Red }
}

exit $exitCode
