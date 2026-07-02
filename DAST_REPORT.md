# Informe DAST — Prediktia

| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-07-02 |
| **Versión analizada** | Backend FastAPI con hardening de seguridad |
| **Objetivo** | `http://127.0.0.1:8000` |
| **Entorno de prueba** | `APP_ENV=production`, `FRONTEND_URL=http://localhost:3000` |

---

## Herramienta utilizada

| Herramienta | Versión / imagen | Uso |
|-------------|------------------|-----|
| **OWASP ZAP Baseline** | `ghcr.io/zaproxy/zaproxy:stable` (ZAP 2.17.0) | Escaneo automatizado pasivo + spider ligero |
| **Probes dinámicos** | `dast/probe_security.py` | Cabeceras, CORS, auth, validación, superficie expuesta |
| **curl / httpx** | — | Verificación puntual (rate limit, redirects) |

**Artefactos generados:**

- `dast/zap-report.html`
- `dast/zap-report.json`
- `dast/probe-results.json`

---

## Objetivo

Verificar que las medidas de hardening aplicadas eliminan los hallazgos **Alto**, **Medio** y **Bajo** detectados en el informe DAST anterior, sin alterar la lógica de negocio, el frontend ni el flujo de autenticación existente.

**Alcance:** API FastAPI en modo producción simulado (`APP_ENV=production`).

---

## Metodología

1. Arrancar la API con `backend/run_production_dast.ps1` (`APP_ENV=production`, `--no-server-header`).
2. Ejecutar `dast/probe_security.py` contra `http://127.0.0.1:8000`.
3. Ejecutar `dast/zap-baseline.ps1` (Docker + imagen oficial ZAP).
4. Clasificar hallazgos según `riskcode` de ZAP (0=Info, 1=Bajo, 2=Medio, 3=Alto) y probes (`pass` / `warn` / `fail`).

---

## Medidas de remediación implementadas

| # | Hallazgo original | Remediación | Archivo(s) |
|---|-------------------|-------------|------------|
| 1 | Endpoints `/debug/*` públicos | Router `debug_latam` **no registrado** cuando `APP_ENV=production` | `app/main.py`, `app/config.py` |
| 2 | CORS `allow_origins=["*"]` | CORS restringido a `FRONTEND_URL` en producción | `app/main.py`, `app/config.py` |
| 3 | Sin rate limiting en auth | Middleware `AuthRateLimitMiddleware` en `POST /auth/login` y `/auth/register` | `app/middleware/auth_rate_limit.py` |
| 4 | Cabeceras de seguridad ausentes | `SecurityHeadersMiddleware` (HSTS, CSP, X-Frame-Options, etc.) | `app/middleware/security_headers.py` |
| 5 | `/docs` y `/openapi.json` públicos | Deshabilitados en producción (`docs_url=None`, sin ruta custom OpenAPI) | `app/main.py` |
| 6 | `Server: uvicorn` expuesto | `--no-server-header` en uvicorn + eliminación en middleware | `run_production_dast.ps1`, middleware |
| 7 | Errores PostgreSQL en debug | Respuestas genéricas `database_unavailable` (sin stack ni psycopg2) | `app/services/acca_persistence_impl.py` |
| 8 | Contenido cacheable (ZAP info) | `Cache-Control: no-store` + `Pragma: no-cache` | `app/middleware/security_headers.py` |

**Sin cambios en:** lógica de negocio (`smart_acca`, `value_bets`, pagos, fixtures), frontend, ni handlers de autenticación (`login`/`register`/`JWT`).

---

## Endpoints expuestos (APP_ENV=production)

### Rutas públicas operativas

| Método | Ruta | HTTP |
|--------|------|------|
| GET | `/health` | 200 |
| GET | `/health/db` | 200 |
| GET | `/matches` | 200 |
| GET | `/value-bets` | 200 |
| GET | `/acca` | 200 |
| GET | `/acca/history` | 200 |

### Rutas deshabilitadas en producción

| Método | Ruta | HTTP |
|--------|------|------|
| GET | `/debug/*` | **404** |
| GET | `/docs` | **404** |
| GET | `/openapi.json` | **404** |

### Rutas protegidas (401 sin token)

| Método | Ruta |
|--------|------|
| GET/PATCH | `/auth/me`, `/auth/me/password` |
| GET | `/payments/history` |
| POST | `/payments/webpay/create` |

### Rate limiting verificado

12 solicitudes consecutivas `POST /auth/login` → HTTP **429** a partir del límite configurado (`AUTH_RATE_LIMIT_MAX=10` / ventana 60 s).

---

## Resultados

### Resumen ejecutivo — probes (`probe_security.py`)

| Probe | Estado |
|-------|--------|
| Cabeceras de seguridad HTTP | **pass** (todas presentes) |
| CORS origen malicioso | **pass** (sin `Access-Control-Allow-Origin: *`) |
| Auth rutas protegidas | **pass** (401) |
| Validación parámetros | **pass** |
| Exposición errores 404 | **pass** |
| OpenAPI / secretos | **pass** (404 en producción) |
| Endpoints `/debug/*` | **info** (404 — no expuestos) |
| `/health/db` | **pass** |

**Probes con `warn` o `fail`:** **0**

### Resumen ejecutivo — OWASP ZAP Baseline

```
FAIL-NEW: 0    FAIL-INPROG: 0
WARN-NEW: 0    WARN-INPROG: 0
INFO: 0        IGNORE: 0
PASS: 66
Exit code: 0
```

### Conteo de riesgo (objetivo del informe)

| Nivel | Anterior | Actual |
|-------|----------|--------|
| **Alto** | 1 | **0** |
| **Medio** | 4 | **0** |
| **Bajo** | 2 | **0** |
| Informativo (ZAP riskcode=0) | — | 1 tipo (*Non-Storable Content*, riskcode 0) |

> La alerta informativa de ZAP (`riskcode: 0`) confirma que `Cache-Control: no-store` está activo; no se clasifica como hallazgo Alto/Medio/Bajo.

---

## Vulnerabilidades encontradas

### Alto — **0 hallazgos**

No se detectaron vulnerabilidades de nivel Alto.

### Medio — **0 hallazgos**

No se detectaron vulnerabilidades de nivel Medio.

### Bajo — **0 hallazgos**

No se detectaron vulnerabilidades de nivel Bajo.

---

## Verificación por categoría (post-remediación)

| Categoría | Resultado |
|-----------|-----------|
| SQL Injection | **No encontrada** |
| Bypass de autenticación | **No encontrada** |
| CORS permisivo (`*`) | **No encontrada** (producción) |
| Endpoints debug expuestos | **No encontrada** (404 en producción) |
| Swagger/OpenAPI público | **No encontrada** (404 en producción) |
| Cabeceras de seguridad ausentes | **No encontrada** |
| Rate limiting ausente | **No encontrada** |
| Exposición errores PostgreSQL (debug) | **No encontrada** |
| Encabezado `Server: uvicorn` | **No encontrada** |
| Stack trace en 404 | **No encontrada** |
| Open Redirect Webpay | **No encontrada** |

---

## Cabeceras HTTP verificadas (`GET /health`)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Permissions-Policy: geolocation=(), microphone=(), camera=()
X-XSS-Protection: 0
Cache-Control: no-store, no-cache, must-revalidate, private
Pragma: no-cache
(server header: ausente)
```

---

## Recomendaciones operativas

1. Desplegar siempre con `APP_ENV=production` y `FRONTEND_URL` apuntando al dominio real del frontend.
2. Mantener `JWT_SECRET` fuerte y único por entorno (no usar el default de desarrollo).
3. Repetir `dast/zap-baseline.ps1` en CI/staging tras cada cambio de superficie API.
4. En desarrollo local (`APP_ENV=development`), `/debug/*` y `/docs` siguen disponibles para diagnóstico.

---

## Comandos para reproducir

```powershell
# Terminal 1 — API en modo producción (DAST)
cd backend
.\run_production_dast.ps1

# Terminal 2 — Probes + ZAP
cd backend
.\.venv\Scripts\python.exe ..\dast\probe_security.py http://127.0.0.1:8000
cd ..
.\dast\zap-baseline.ps1
```

---

*Informe regenerado tras hardening de seguridad. Sin commit ni push.*
