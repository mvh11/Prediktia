import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import acca, debug_latam, matches, value_bets
from app.config import Settings, get_settings
from app.services.db_health import build_db_health_payload

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
        logger.info("DB disabled — no DATABASE_URL; stateless mode enabled")
    else:
        try:
            import sqlalchemy
            from sqlalchemy import text

            from app.db.session import get_engine

            _ = sqlalchemy.__version__
            eng = get_engine(settings.database_url)
            if eng is None:
                logger.warning(
                    "DB unavailable → running stateless mode (engine no creado; revisa DATABASE_URL y drivers)."
                )
            else:
                with eng.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    reg = conn.execute(
                        text("SELECT to_regclass('public.acca_history')::text")
                    ).scalar()
                    has_status = conn.execute(
                        text(
                            """
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name = 'acca_history'
                              AND column_name = 'status'
                            LIMIT 1
                            """
                        )
                    ).scalar()
                    has_settled_at = conn.execute(
                        text(
                            """
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name = 'acca_history'
                              AND column_name = 'settled_at'
                            LIMIT 1
                            """
                        )
                    ).scalar()
                    try:
                        conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
                    except Exception:
                        pass

                logger.info("DB connected — ping OK")
                app.state.db_mode = "connected"
                if not reg:
                    logger.warning(
                        "Alembic pending — tabla public.acca_history no encontrada. "
                        "Ejecuta desde backend/: alembic upgrade head"
                    )
                elif not has_status:
                    logger.warning(
                        "Alembic pending — falta columna acca_history.status. Ejecuta: alembic upgrade head"
                    )
                elif not has_settled_at:
                    logger.warning(
                        "Alembic pending — falta columna acca_history.settled_at. Ejecuta: alembic upgrade head"
                    )
        except ImportError as exc:
            logger.warning(
                "DB unavailable → running stateless mode (SQLAlchemy no instalado: %s). "
                "Instala: pip install -r requirements.txt",
                exc,
            )
        except Exception:
            logger.warning(
                "DB unavailable → running stateless mode (no se pudo verificar PostgreSQL). "
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
