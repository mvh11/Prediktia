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


def ensure_database_schema(database_url: str | None, *, force: bool = False) -> bool:
    """
    Idempotente: aplica migraciones una vez por proceso (salvo force=True).
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
        _schema_ready = ok
        _schema_last_error = err
        return ok


def schema_bootstrap_error() -> str | None:
    return _schema_last_error
