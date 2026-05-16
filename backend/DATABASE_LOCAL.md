# PostgreSQL local (Prediktia)

## 1. Levantar PostgreSQL

En la raíz del repositorio (donde está `docker-compose.yml`):

```powershell
docker compose up -d
```

Espera a que el contenedor esté healthy (`docker compose ps`).

## 2. Variables de entorno

Copia `backend/.env.example` → `backend/.env` y define al menos:

- `API_FOOTBALL_KEY`
- `DATABASE_URL=postgresql+psycopg2://prediktia:password@localhost:5432/prediktia_db`

## 3. Migraciones Alembic

Con el venv del backend activo y el directorio **backend/** como cwd:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql+psycopg2://prediktia:password@localhost:5432/prediktia_db"
alembic upgrade head
```

(O define `DATABASE_URL` en `.env`; `alembic/env.py` ya la lee vía `get_settings()`.)

## 4. Verificar conexión

- API: `GET http://127.0.0.1:8000/health/db` → con migraciones al día debe incluir `"database": "connected"`. Si faltan tablas o columnas, verás `"database": "error"`, `"migrations_pending": true` y un `detail` con la acción (`alembic upgrade head`).
- CLI (opcional):

```powershell
docker compose exec postgres psql -U prediktia -d prediktia_db -c "SELECT 1;"
```

## 5. Arrancar FastAPI

Desde `backend/`:

```powershell
.\run_dev.ps1
```

Genera una ACCA (`GET /acca`); debe persistirse y aparecer en `GET /acca/history`.

## Liquidación manual (desarrollo)

`PATCH /acca/history/{acca_id}` con cuerpo JSON, por ejemplo:

```json
{"status": "won", "roi": 0.42}
```

Valores de `status`: `pending`, `won`, `lost`.
