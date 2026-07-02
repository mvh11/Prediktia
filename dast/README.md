# DAST — OWASP ZAP (Prediktia)

Preparación para análisis dinámico de seguridad **sin modificar la aplicación**.

## Requisitos

| Componente | Versión / notas |
|------------|-----------------|
| Backend API | `uvicorn app.main:app --host 127.0.0.1 --port 8000` desde `backend/` |
| Docker Desktop | Daemon activo (Linux engine) |
| Imagen ZAP | `ghcr.io/zaproxy/zaproxy:stable` (oficial OWASP) |
| Python (probes) | `backend/.venv` con `httpx` |

## Arrancar el objetivo

```powershell
cd backend
.\run_dev.ps1
# o
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

Comprobar: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`

### Modo producción (DAST / staging)

Para validar hardening (debug/docs deshabilitados, CORS restringido):

```powershell
cd backend
.\run_production_dast.ps1
```

Equivalente manual:

```powershell
$env:APP_ENV = "production"
$env:FRONTEND_URL = "http://localhost:3000"
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --no-server-header
```

## Escaneo baseline con OWASP ZAP

Desde la raíz del repositorio:

```powershell
.\dast\zap-baseline.ps1
```

Parámetros opcionales:

```powershell
.\dast\zap-baseline.ps1 -TargetUrl "http://host.docker.internal:8000"
```

Salida:

- `dast/zap-report.html` — informe HTML de ZAP
- `dast/zap-report.json` — alertas en JSON

> **Nota Windows:** el contenedor ZAP accede al host vía `host.docker.internal`. El script comprueba salud en `127.0.0.1:8000` antes de lanzar Docker.

### Comando Docker equivalente

```powershell
docker run --rm `
  -v "${PWD}/dast:/zap/wrk:rw" `
  -t ghcr.io/zaproxy/zaproxy:stable `
  zap-baseline.py `
  -t http://host.docker.internal:8000 `
  -r zap-report.html `
  -J zap-report.json `
  -I `
  -s `
  --autooff
```

## Probes manuales (complemento DAST)

```powershell
cd backend
.\.venv\Scripts\python.exe ..\dast\probe_security.py http://127.0.0.1:8000 > ..\dast\probe-results.json
```

El script verifica: inventario de rutas, cabeceras HTTP, CORS, auth, validación de parámetros, exposición de errores y endpoints `/debug/*`.

## Superficie de ataque (OpenAPI)

16 rutas documentadas en `/openapi.json`. Ver inventario completo en `DAST_REPORT.md`.

## Alcance recomendado para ZAP

| URL base | Incluir | Motivo |
|----------|---------|--------|
| `http://host.docker.internal:8000` | Sí | API FastAPI (objetivo principal) |
| `http://host.docker.internal:3000` | Opcional | Frontend Next.js (si está en ejecución) |

Para escaneo API-only, importar OpenAPI en ZAP Desktop: **Import → OpenAPI** → `http://127.0.0.1:8000/openapi.json`

## Fecha de preparación

2026-07-02
