# Pruebas unitarias — Prediktia (backend)

Suite de tests con **pytest** para la lógica de negocio del backend FastAPI. No modifica la aplicación ni el frontend; solo valida motores, normalizadores, validadores y repositorios.

## Requisitos

Desde la carpeta `backend/`:

```bash
pip install -r requirements.txt
pip install -r tests/requirements-dev.txt
```

Incluye `pytest`, `pytest-cov`, `pytest-mock` y `httpx` (requerido por `TestClient`).

## Estructura

```
tests/
├── conftest.py              # path del proyecto + fixtures globales
├── fixtures/                # datos de prueba (p. ej. API-Football mock)
├── unit/
│   ├── services/            # Poisson, EV, value bets, permisos, Webpay…
│   ├── db/                  # normalizadores de URL
│   ├── repositories/        # usuarios y pagos (Session mockeada)
│   └── schemas/             # validadores Pydantic
└── requirements-dev.txt     # pytest, pytest-mock, pytest-cov
```

## Ejecutar pruebas

Posiciónate en **`backend/`** (donde está `pytest.ini`):

```bash
pytest
```

Salida detallada por test:

```bash
pytest -v
```

Cada ejecución de `pytest` incluye **cobertura en consola** (`term-missing`) y genera el reporte **HTML** en `backend/htmlcov/index.html`.

Para ejecutar tests sin medir cobertura (más rápido):

```bash
pytest --no-cov
```

Solo reporte de cobertura (consola + HTML):

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html:htmlcov
```

Opciones útiles:

```bash
# Un módulo concreto
pytest tests/unit/services/test_poisson.py -v

# Un test concreto
pytest tests/unit/services/test_ev_engine.py::TestComputeEvMetrics::test_positive_ev_when_model_beats_market -v

# Abrir reporte HTML (Windows)
start htmlcov/index.html
```

## Qué se prueba

| Área | Archivo(s) | Notas |
|------|------------|--------|
| Motor Poisson | `test_poisson.py` | lambdas, probabilidades 1X2/O-U/BTTS |
| Motor EV | `test_ev_engine.py` | `implied_probability`, `compute_ev_metrics` |
| Value Bets | `test_value_bets.py` | grades, quotes, mock picks, orden Free |
| Permisos / tiers | `test_plan_permissions.py` | `normalize_tier`, caps |
| Ligas | `test_league_*.py` | formato y prioridad |
| ACCA filtros | `test_acca_fixture_filter.py` | timestamps, kickoff, status |
| Smart ACCA | `test_smart_acca.py` | perfiles de riesgo, generate, calendar |
| Candidatos ACCA | `test_acca_candidates.py`, `test_acca_odds.py` | pool Poisson + cuotas |
| API-Football | `test_football_api.py` | caché, singleflight, HTTP mock |
| Rutas FastAPI | `test_api_routes.py`, `test_auth_routes.py`, `test_payments_routes.py` | TestClient + overrides |
| Auth deps | `test_auth_deps.py` | JWT + Bearer |
| DB health | `test_db_health.py` | engine mock |
| Persistencia ACCA | `test_acca_persistence.py` | facade sin PostgreSQL |
| Auth | `test_passwords.py`, `test_auth_tokens.py` | bcrypt + JWT |
| Webpay | `test_webpay.py` | HTTP mockeado (`unittest.mock`) |
| DB URL | `test_url.py` | normalización Neon/Render |
| Repositorios | `test_*_repository.py` | SQLAlchemy Session mock |
| Schemas | `test_*_schemas.py` | validación Pydantic |

Las dependencias externas (**API-Football**, **PostgreSQL**, **Transbank** en red) no se llaman en tiempo real: se usan fixtures locales y `unittest.mock` / `pytest-mock`.

## CI / entorno académico

- No se requiere `DATABASE_URL` para ejecutar la suite.
- No se requiere `API_FOOTball_KEY` válida (Settings usa valores de prueba en tests de JWT/Webpay).
- Si algún test falla por dependencias faltantes, reinstala: `pip install -r requirements.txt -r tests/requirements-dev.txt`.
