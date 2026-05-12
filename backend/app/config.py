from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno y archivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_football_key: str
    api_football_base_url: str = "https://v3.football.api-sports.io"
    # Timeout (connect, read) en segundos; sin reintentos (una sola petición HTTP).
    api_football_timeout_connect_seconds: float = 10.0
    api_football_timeout_read_seconds: float = 25.0
    # 0 = desactiva caché. >0 reutiliza la última respuesta OK por fecha durante ese TTL (desarrollo).
    matches_upstream_cache_ttl_seconds: int = 90


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de Settings (caché por proceso)."""
    return Settings()
