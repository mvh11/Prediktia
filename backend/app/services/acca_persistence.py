"""
Persistencia ACCA: carga diferida de SQLAlchemy.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.config import Settings

logger = logging.getLogger(__name__)

_db_impl: tuple[Callable[..., Any], Callable[..., Any]] | str | None = None


def _resolve_db_impl() -> tuple[Callable[..., Any], Callable[..., Any]] | None:
    global _db_impl
    if _db_impl == "disabled":
        return None
    if isinstance(_db_impl, tuple):
        return _db_impl

    try:
        import sqlalchemy  # noqa: F401

        _ = sqlalchemy.__version__
    except ImportError as exc:
        logger.warning("SQLAlchemy no instalado: persistencia desactivada (%s)", exc)
        _db_impl = "disabled"
        return None

    try:
        from app.services.acca_persistence_impl import (
            list_acca_history as _list_acca_history,
            persist_smart_acca as _persist_smart_acca,
        )

        _db_impl = (_persist_smart_acca, _list_acca_history)
        return _db_impl
    except Exception as exc:
        logger.warning("No se pudo cargar persistencia ORM: %s", exc, exc_info=True)
        _db_impl = "disabled"
        return None


def persist_smart_acca(settings: Settings, result: dict[str, Any]) -> tuple[str | None, str | None]:
    if not settings.database_url:
        return None, "no_database_url"
    impl = _resolve_db_impl()
    if impl is None:
        return None, "no_sqlalchemy_impl_or_disabled"
    try:
        return impl[0](settings, result)
    except Exception as exc:
        logger.exception("persist_smart_acca: error")
        return None, f"{type(exc).__name__}: {exc}"


def list_acca_history(settings: Settings, *, limit: int = 50) -> list[dict[str, Any]]:
    if not settings.database_url:
        return []
    impl = _resolve_db_impl()
    if impl is None:
        return []
    try:
        return impl[1](settings, limit=limit)
    except Exception:
        logger.exception("list_acca_history: error")
        return []


def fetch_acca_db_last_debug(settings: Settings) -> dict[str, Any]:
    from app.services.acca_persistence_impl import fetch_acca_db_last_debug as _impl

    return _impl(settings)
