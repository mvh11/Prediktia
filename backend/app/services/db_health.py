"""Comprobación de conectividad PostgreSQL (sin acoplar al arranque de FastAPI)."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)

_SAFE_URL_RE = re.compile(r"//([^:]+):([^@]+)@")


def _redact_database_url(url: str) -> str:
    return _SAFE_URL_RE.sub(r"//\1:***@", url, count=1)


def database_connected(settings: Settings) -> bool:
    """True si DATABASE_URL está definida, PostgreSQL responde y existe acca_history."""
    if not settings.database_url:
        return False
    try:
        from sqlalchemy import text

        from app.db.session import get_engine

        eng = get_engine(settings.database_url)
        if eng is None:
            return False
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            tbl = conn.execute(text("SELECT to_regclass('public.acca_history')::text")).scalar()
            return bool(tbl)
    except Exception as exc:
        logger.debug("database_connected: %s", exc)
        return False


def build_db_health_payload(settings: Settings) -> dict[str, Any]:
    """
    Carga útil para GET /health/db.
    Éxito mínimo: {"database": "connected"}.
    """
    if not settings.database_url:
        return {
            "database": "disabled",
            "detail": "DATABASE_URL no configurada; modo stateless.",
            "stateless": True,
        }

    try:
        import sqlalchemy
        from sqlalchemy import text

        from app.db.session import get_engine

        _ = sqlalchemy.__version__
    except ImportError as exc:
        return {
            "database": "error",
            "detail": f"SQLAlchemy no disponible: {exc}",
            "stateless": True,
        }

    url = settings.database_url
    try:
        eng = get_engine(url)
        if eng is None:
            return {
                "database": "error",
                "detail": "No se pudo crear el engine (revisa URL y drivers, p. ej. psycopg2-binary).",
                "database_url_preview": _redact_database_url(url),
            }
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            try:
                alembic_rev = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
            except Exception:
                alembic_rev = None
            tbl = conn.execute(
                text("SELECT to_regclass('public.acca_history')::text")
            ).scalar()
            if not tbl:
                logger.warning(
                    "Alembic pending — tabla public.acca_history no existe; ejecuta: alembic upgrade head"
                )
                return {
                    "database": "error",
                    "detail": "PostgreSQL responde pero faltan tablas (migraciones pendientes). Ejecuta: alembic upgrade head",
                    "alembic_revision": alembic_rev,
                    "migrations_pending": True,
                }
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
            if not has_status:
                logger.warning(
                    "Alembic pending — falta columna acca_history.status; ejecuta: alembic upgrade head"
                )
                return {
                    "database": "error",
                    "detail": "Migraciones desactualizadas (falta acca_history.status). Ejecuta: alembic upgrade head",
                    "alembic_revision": alembic_rev,
                    "migrations_pending": True,
                }
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
            if not has_settled_at:
                logger.warning(
                    "Alembic pending — falta columna acca_history.settled_at; ejecuta: alembic upgrade head"
                )
                return {
                    "database": "error",
                    "detail": "Migraciones desactualizadas (falta acca_history.settled_at). Ejecuta: alembic upgrade head",
                    "alembic_revision": alembic_rev,
                    "migrations_pending": True,
                }

        out: dict[str, Any] = {"database": "connected"}
        if alembic_rev:
            out["alembic_revision"] = alembic_rev
        return out
    except Exception as exc:
        logger.warning("GET /health/db: conexión fallida (%s)", exc, exc_info=True)
        return {
            "database": "error",
            "detail": str(exc),
            "error_type": type(exc).__name__,
            "database_url_preview": _redact_database_url(url),
        }
