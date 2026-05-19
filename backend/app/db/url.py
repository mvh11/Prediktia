"""Normalización de DATABASE_URL para SQLAlchemy + psycopg2 (Neon, Render, local)."""

from __future__ import annotations


def normalize_database_url(url: str) -> str:
    """
    Acepta postgresql://, postgres:// o postgresql+psycopg2:// y devuelve
    postgresql+psycopg2://… conservando query params (p. ej. sslmode=require).
    """
    raw = url.strip()
    if not raw:
        return raw

    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    scheme, _, rest = raw.partition("://")
    if not rest:
        return raw

    base_scheme = scheme.split("+", 1)[0].lower()
    if base_scheme in ("postgresql", "postgres"):
        return f"postgresql+psycopg2://{rest}"

    return raw
