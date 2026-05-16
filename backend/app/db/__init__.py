"""
Paquete ORM / PostgreSQL.

Las importaciones pesadas (SQLAlchemy) se resuelven al acceder a los símbolos;
`from app.db.base import Base` sigue funcionando para Alembic.
"""

from __future__ import annotations

__all__ = ["Base", "get_engine", "session_scope"]


def __getattr__(name: str):
    if name == "Base":
        from app.db.base import Base

        return Base
    if name == "get_engine":
        from app.db.session import get_engine

        return get_engine
    if name == "session_scope":
        from app.db.session import session_scope

        return session_scope
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
