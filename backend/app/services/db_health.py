"""Comprobación de conectividad PostgreSQL (Neon, Render, local)."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text

from app.config import Settings
from app.db.migrations import ensure_database_schema, schema_bootstrap_error
from app.db.session import get_engine

logger = logging.getLogger(__name__)

_SAFE_URL_RE = re.compile(r"//([^:]+):([^@]+)@")


def _redact_database_url(url: str) -> str:
    return _SAFE_URL_RE.sub(r"//\1:***@", url, count=1)


def _acca_history_ready(conn) -> bool:
    tbl = conn.execute(text("SELECT to_regclass('public.acca_history')::text")).scalar()
    if not tbl:
        return False
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
    return bool(has_status)


def database_connected(settings: Settings, *, try_migrate: bool = False) -> bool:
    """
    True si DATABASE_URL está definida, PostgreSQL responde y existe acca_history.
    Con try_migrate=True intenta aplicar migraciones Alembic si falta la tabla.
    """
    if not settings.database_url:
        return False
    try:
        eng = get_engine(settings.database_url)
        if eng is None:
            return False
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            if _acca_history_ready(conn):
                return True
        if try_migrate and ensure_database_schema(settings.database_url):
            with eng.connect() as conn:
                return _acca_history_ready(conn)
        return False
    except Exception as exc:
        logger.debug("database_connected: %s", exc)
        return False


def database_status_message(settings: Settings) -> str | None:
    """Mensaje amigable para UI; None si el historial está operativo."""
    if not settings.database_url:
        logger.info("database_status_message: DATABASE_URL no configurada")
        return "No hay historial disponible."

    eng = get_engine(settings.database_url)
    if eng is None:
        logger.warning("database_status_message: engine no disponible")
        return "No hay historial disponible."

    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            if _acca_history_ready(conn):
                return None
    except Exception as exc:
        logger.warning("database_status_message: ping falló — %s", exc, exc_info=True)
        return "No hay historial disponible."

    if ensure_database_schema(settings.database_url):
        try:
            with eng.connect() as conn:
                if _acca_history_ready(conn):
                    return None
        except Exception as exc:
            logger.warning("database_status_message: re-check falló — %s", exc)

    err = schema_bootstrap_error()
    if err:
        logger.error("database_status_message: esquema acca_history no listo — %s", err)
    return "No hay historial disponible."


def inspect_db_health(settings: Settings) -> dict[str, Any]:
    """
    Respuesta simple para GET /health/db (Render / Neon).
    Éxito: {"database": "ok", "acca_history_exists": true}
    """
    if not settings.database_url:
        return {"database": "disabled", "acca_history_exists": False}

    try:
        eng = get_engine(settings.database_url)
        if eng is None:
            return {"database": "error", "acca_history_exists": False}

        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            if _acca_history_ready(conn):
                return {"database": "ok", "acca_history_exists": True}

        if ensure_database_schema(settings.database_url):
            with eng.connect() as conn:
                if _acca_history_ready(conn):
                    return {"database": "ok", "acca_history_exists": True}

        err = schema_bootstrap_error()
        logger.error("inspect_db_health: acca_history no lista — %s", err)
        return {"database": "error", "acca_history_exists": False}
    except Exception as exc:
        logger.warning("inspect_db_health: %s", exc, exc_info=True)
        return {"database": "error", "acca_history_exists": False}


def build_db_health_payload(settings: Settings) -> dict[str, Any]:
    """
    Carga útil para GET /health/db.
    Éxito mínimo: {"database": "connected"}.
    """
    if not settings.database_url:
        return {
            "database": "disabled",
            "detail": "DATABASE_URL no configurada; modo sin persistencia de historial.",
            "stateless": True,
        }

    try:
        import sqlalchemy

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
                "detail": "No se pudo crear el engine (revisa URL y psycopg2-binary).",
                "database_url_preview": _redact_database_url(url),
            }
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            try:
                alembic_rev = conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).scalar()
            except Exception:
                alembic_rev = None

            if not _acca_history_ready(conn):
                ensure_database_schema(settings.database_url)
                with eng.connect() as conn2:
                    if _acca_history_ready(conn2):
                        try:
                            alembic_rev = conn2.execute(
                                text("SELECT version_num FROM alembic_version LIMIT 1")
                            ).scalar()
                        except Exception:
                            pass
                    else:
                        err = schema_bootstrap_error()
                        return {
                            "database": "error",
                            "detail": (
                                "PostgreSQL responde pero acca_history no está lista. "
                                + (err or "Revisa logs de migración en Render.")
                            ),
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
