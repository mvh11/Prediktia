"""

Persistencia ACCA: carga diferida de SQLAlchemy.



Si SQLAlchemy no está instalado o el stack DB falla al importar, el API arranca

igual en modo stateless (sin persistencia).

"""



from __future__ import annotations



import logging

from typing import Any, Callable



from app.config import Settings



logger = logging.getLogger(__name__)



# None = aún no probado; tuple = (persist, list, settle); "disabled" = no reintentar

_db_impl: tuple[Callable[..., Any], Callable[..., Any], Callable[..., Any]] | str | None = None





def _resolve_db_impl() -> tuple[Callable[..., Any], Callable[..., Any], Callable[..., Any]] | None:

    """Importa el backend real solo si SQLAlchemy está disponible."""

    global _db_impl

    if _db_impl == "disabled":

        return None

    if isinstance(_db_impl, tuple):

        return _db_impl



    try:

        import sqlalchemy  # noqa: F401



        _ = sqlalchemy.__version__

    except ImportError as exc:

        logger.warning(

            "DB unavailable → running stateless mode (SQLAlchemy no instalado: %s). "

            "Instala dependencias: pip install -r requirements.txt",

            exc,

        )

        _db_impl = "disabled"

        return None



    try:

        from app.services.acca_persistence_impl import (

            list_acca_history as _list_acca_history,

            persist_smart_acca as _persist_smart_acca,

            settle_acca_history as _settle_acca_history,

        )



        _db_impl = (_persist_smart_acca, _list_acca_history, _settle_acca_history)

        return _db_impl

    except Exception as exc:

        logger.warning(

            "DB unavailable → running stateless mode (no se pudo cargar el stack ORM: %s)",

            exc,

            exc_info=True,

        )

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
        logger.exception("persist_smart_acca: error en fachada traceback=logged")
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

        logger.exception("list_acca_history: error no controlado en fachada; se devuelve [].")

        return []





def settle_acca_history(

    settings: Settings,

    acca_id: str,

    *,

    status: str,

    roi: float | None = None,

) -> str:

    """Delegación a impl. Retorna código: ok | not_found | unavailable | error."""

    if not settings.database_url:

        return "unavailable"

    impl = _resolve_db_impl()

    if impl is None:

        return "unavailable"

    try:

        return impl[2](settings, acca_id, status=status, roi=roi)

    except Exception:

        logger.exception("settle_acca_history: error en fachada.")

        return "error"


def fetch_acca_db_last_debug(settings: Settings) -> dict[str, Any]:
    """Última fila acca_history / predictions y conteos (misma URL que persistencia)."""
    from app.services.acca_persistence_impl import fetch_acca_db_last_debug as _impl

    return _impl(settings)

