import logging
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import acca, auth, debug_latam, matches, payments, value_bets
from app.config import Settings, get_settings
from app.db.migrations import ensure_database_schema
from app.middleware.auth_rate_limit import AuthRateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.db_health import database_connected, inspect_db_health

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

    if settings.is_production():
        logger.info("APP_ENV=production — debug/docs deshabilitados, CORS restringido")
    else:
        logger.info("APP_ENV=%s — modo desarrollo", settings.app_env)

    if not settings.database_url:
        logger.info("DB disabled — no DATABASE_URL; historial ACCA sin persistencia")
    else:

        def _bootstrap_db() -> None:
            try:
                import sqlalchemy

                _ = sqlalchemy.__version__
                if ensure_database_schema(settings.database_url):
                    if database_connected(settings):
                        logger.info("DB connected — Neon/PostgreSQL listo (acca_history OK)")
                        app.state.db_mode = "connected"
                    else:
                        logger.warning(
                            "DB: migraciones OK pero acca_history no verificada (historial best-effort)"
                        )
                else:
                    from app.db.migrations import schema_bootstrap_error

                    logger.warning(
                        "DB bootstrap falló (%s). /matches y /acca siguen activos.",
                        schema_bootstrap_error() or "error desconocido",
                    )
            except ImportError as exc:
                logger.warning("DB unavailable — SQLAlchemy: %s", exc)
            except Exception:
                logger.warning("DB bootstrap excepción (API sigue sin bloquear)", exc_info=True)

        threading.Thread(target=_bootstrap_db, name="db-bootstrap", daemon=True).start()
        logger.info("DB bootstrap en segundo plano (no bloquea /matches ni /value-bets)")

    yield

    if getattr(app.state, "db_mode", None) == "connected":
        logger.info("DB disconnected — API shutdown")
    logger.info("Prediktia API shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Factory de la aplicacion; permite tests con distintos Settings."""
    cfg = settings or get_settings()
    production = cfg.is_production()

    app = FastAPI(
        lifespan=lifespan,
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_allow_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthRateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(auth.router)
    app.include_router(payments.router)
    app.include_router(matches.router)
    app.include_router(value_bets.router)
    if cfg.debug_routes_enabled():
        app.include_router(debug_latam.router)
    app.include_router(acca.router)

    if not production:

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
        Estado de PostgreSQL / acca_history.
        Éxito: {"database": "ok", "acca_history_exists": true}
        """
        payload = inspect_db_health(settings)
        if payload.get("database") == "ok":
            logger.info("DB ok (health/db) acca_history_exists=%s", payload.get("acca_history_exists"))
        elif payload.get("database") == "disabled":
            logger.info("DB disabled (health/db)")
        else:
            logger.warning("DB health check: %s", payload)
        return payload

    return app


app = create_app()
