"""Motor SQLAlchemy (singleton por proceso)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.url import normalize_database_url

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None
_bound_url: str | None = None


def get_engine(database_url: str | None) -> Engine | None:
    """Crea o reutiliza el engine para la URL dada."""
    global _engine, _SessionLocal, _bound_url
    if not database_url:
        return None
    database_url = normalize_database_url(database_url)
    if _engine is not None and _bound_url == database_url:
        return _engine
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            logger.debug("get_engine: dispose del engine anterior falló (se ignora).", exc_info=True)
    try:
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            future=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
        _bound_url = database_url
        logger.info("DB: SQLAlchemy engine inicializado.")
    except Exception:
        logger.warning(
            "DB: no se pudo crear el engine (URL inválida o driver faltante). "
            "Modo stateless para persistencia.",
            exc_info=True,
        )
        _engine = None
        _SessionLocal = None
        _bound_url = None
        return None
    return _engine


@contextmanager
def session_scope(database_url: str | None) -> Generator[Session | None, None, None]:
    """Context manager: commit al salir sin error, rollback si excepción."""
    eng = get_engine(database_url)
    if eng is None or _SessionLocal is None:
        yield None
        return
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
