"""Aplicación automática de migraciones Alembic (Neon / producción)."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from app.db.url import normalize_database_url

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_schema_lock = threading.Lock()
_schema_ready = False
_schema_last_error: str | None = None


def run_alembic_upgrade_head(database_url: str) -> tuple[bool, str | None]:
    """Ejecuta `alembic upgrade head` contra la URL indicada."""
    from alembic import command
    from alembic.config import Config

    normalized = normalize_database_url(database_url)
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", normalized)

    try:
        command.upgrade(cfg, "head")
        logger.info("DB: migraciones Alembic aplicadas (upgrade head).")
        return True, None
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.warning("DB: falló alembic upgrade head — %s", msg, exc_info=True)
        return False, msg


def create_schema_fallback(database_url: str) -> tuple[bool, str | None]:
    """Crea tablas desde metadata SQLAlchemy si Alembic no pudo aplicarse."""
    from app.db.base import Base
    from app.db.session import get_engine

    try:
        from app.db import models as _models  # noqa: F401

        _ = _models
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.warning("DB: no se pudieron cargar modelos ORM — %s", msg, exc_info=True)
        return False, msg

    eng = get_engine(database_url)
    if eng is None:
        return False, "engine_unavailable"

    try:
        Base.metadata.create_all(bind=eng)
        logger.info("DB: esquema creado con Base.metadata.create_all (fallback).")
        return True, None
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.warning("DB: falló create_all — %s", msg, exc_info=True)
        return False, msg


def ensure_database_schema(database_url: str | None, *, force: bool = False) -> bool:
    """
    Idempotente: aplica migraciones una vez por proceso (salvo force=True).
    Si Alembic falla, intenta create_all como respaldo.
    """
    global _schema_ready, _schema_last_error

    if not database_url:
        return False

    if _schema_ready and not force:
        return True

    with _schema_lock:
        if _schema_ready and not force:
            return True

        ok, err = run_alembic_upgrade_head(database_url)
        if not ok:
            ok_fb, err_fb = create_schema_fallback(database_url)
            if ok_fb:
                ok, err = True, None
            elif err_fb:
                err = f"{err}; fallback: {err_fb}" if err else err_fb

        _schema_ready = ok
        _schema_last_error = err
        return ok


def schema_bootstrap_error() -> str | None:
    return _schema_last_error


def truncate_acca_history(database_url: str | None) -> tuple[bool, str | None]:
    """Vacía acca_history para demo (TRUNCATE … RESTART IDENTITY). Solo si la tabla existe."""
    if not database_url:
        return False, "no_database_url"

    from sqlalchemy import text

    from app.db.session import get_engine

    eng = get_engine(database_url)
    if eng is None:
        return False, "engine_unavailable"

    try:
        with eng.begin() as conn:
            exists = conn.execute(
                text("SELECT to_regclass('public.acca_history')::text")
            ).scalar()
            if not exists:
                return True, None
            conn.execute(
                text("TRUNCATE TABLE acca_history RESTART IDENTITY CASCADE")
            )
        logger.info("DB: acca_history truncada (demo).")
        return True, None
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.warning("DB: truncate acca_history falló — %s", msg, exc_info=True)
        return False, msg
