import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import acca, debug_latam, matches, value_bets
from app.config import Settings, get_settings
from app.db.migrations import ensure_database_schema
from app.services.db_health import build_db_health_payload, database_connected

logger = logging.getLogger("prediktia")


def _setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()

    settings = get_settings()
    app.state.db_mode = "stateless"

    if not settings.database_url:
        logger.info("DB disabled — no DATABASE_URL; historial ACCA sin persistencia")
    else:
        try:
            import sqlalchemy

            _ = sqlalchemy.__version__
            if ensure_database_schema(settings.database_url):
                if database_connected(settings):
                    logger.info("DB connected — Neon/PostgreSQL listo (acca_history OK)")
                    app.state.db_mode = "connected"
                else:
                    logger.warning(
                        "DB: migraciones ejecutadas pero acca_history no verificada; "
                        "historial en modo best-effort"
                    )
            else:
                from app.db.migrations import schema_bootstrap_error

                logger.warning(
                    "DB: no se pudo aplicar el esquema automáticamente (%s). "
                    "Revisa DATABASE_URL en Render (Neon).",
                    schema_bootstrap_error() or "error desconocido",
                )
        except ImportError as exc:
            logger.warning(
                "DB unavailable — SQLAlchemy no instalado (%s). pip install -r requirements.txt",
                exc,
            )
        except Exception:
            logger.warning(
                "DB unavailable — no se pudo conectar a PostgreSQL (Neon). "
                "La API sigue; persistencia ACCA será best-effort.",
                exc_info=True,
            )

    yield

    if getattr(app.state, "db_mode", None) == "connected":
        logger.info("DB disconnected — API shutdown")
    logger.info("Prediktia API shutdown")


# Inicialización mínima: rutas OpenAPI por defecto (/docs, /openapi.json).
# No usar root_path ni desactivar openapi_url en producción (Swagger falla con 404).
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matches.router)
app.include_router(value_bets.router)
app.include_router(debug_latam.router)
app.include_router(acca.router)


@app.get("/openapi.json", include_in_schema=False)
def openapi_schema() -> JSONResponse:
    """Esquema OpenAPI en la ruta estándar (compatible con Render y Swagger UI)."""
    return JSONResponse(app.openapi())


@app.get("/health")
def health() -> dict[str, str]:
    """Comprueba que el servidor responde (útil para pruebas rápidas)."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db(settings: Settings = Depends(get_settings)) -> dict:
    """
    Estado de PostgreSQL. Éxito típico: {"database": "connected"}.
    Si falla la conexión o faltan migraciones, devuelve database=error y detalle (HTTP 200).
    """
    payload = build_db_health_payload(settings)
    if payload.get("database") == "connected":
        logger.info("DB connected (health/db)")
    elif payload.get("database") == "disabled":
        logger.info("DB disabled (health/db) — stateless")
    else:
        logger.warning("DB health check: %s", payload.get("detail", payload))
    return payload
