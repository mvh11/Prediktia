from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db.url import normalize_database_url

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_CANDIDATES = (
    _BACKEND_DIR / ".env",
    _BACKEND_DIR.parent / ".env",
)
_ENV_FILES = tuple(str(p) for p in _ENV_CANDIDATES if p.is_file()) or (str(_BACKEND_DIR / ".env"),)


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno y archivo .env."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_football_key: str
    api_football_base_url: str = "https://v3.football.api-sports.io"
    # Timeout (connect, read) en segundos; sin reintentos (una sola petición HTTP).
    api_football_timeout_connect_seconds: float = 10.0
    api_football_timeout_read_seconds: float = 25.0
    # TTL (s) caché fixtures/odds; mínimo efectivo 300s. Compartido por matches, value y acca.
    matches_upstream_cache_ttl_seconds: int = 300

    # PostgreSQL (opcional). Neon/Render suelen usar postgresql://…?sslmode=require
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
        description="PostgreSQL (Neon, Render, local). Se normaliza a postgresql+psycopg2://",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _coerce_database_url(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return normalize_database_url(text)

    # ACCA: margen (min) antes del kickoff en UTC; 0 = desactivado (solo futuro estricto).
    acca_min_minutes_before_kickoff: int = 0


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de Settings (caché por proceso)."""
    return Settings()
