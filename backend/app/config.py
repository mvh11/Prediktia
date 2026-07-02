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
        env_ignore_empty=True,
    )

    api_football_key: str = Field(
        validation_alias=AliasChoices(
            "API_FOOTBALL_KEY",
            "APIFOOTBALL_KEY",
            "api_football_key",
        ),
    )
    api_football_base_url: str = Field(
        default="https://v3.football.api-sports.io",
        validation_alias=AliasChoices(
            "API_FOOTBALL_BASE_URL",
            "api_football_base_url",
        ),
    )

    @field_validator("api_football_key", mode="before")
    @classmethod
    def _normalize_api_key(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip().strip('"').strip("'")

    @field_validator("api_football_base_url", mode="before")
    @classmethod
    def _normalize_api_base_url(cls, value: object) -> str:
        default = "https://v3.football.api-sports.io"
        if value is None:
            return default
        text = str(value).strip().strip('"').strip("'").rstrip("/")
        if not text:
            return default
        lower = text.lower()
        if "rapidapi.com" in lower:
            return default
        if "api-sports.io" not in lower and "api-football" not in lower:
            return default
        if not text.startswith("http"):
            text = f"https://{text}"
        return text.rstrip("/")
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

    jwt_secret: str = Field(
        default="prediktia-dev-secret-change-in-production",
        validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
    )
    jwt_expire_minutes: int = Field(
        default=60 * 24 * 7,
        validation_alias=AliasChoices("JWT_EXPIRE_MINUTES", "jwt_expire_minutes"),
    )

    # Transbank Webpay Plus (solo backend — nunca exponer al frontend).
    webpay_env: str = Field(
        default="integration",
        validation_alias=AliasChoices("WEBPAY_ENV", "webpay_env"),
    )
    webpay_commerce_code: str = Field(
        default="",
        validation_alias=AliasChoices("WEBPAY_COMMERCE_CODE", "webpay_commerce_code"),
    )
    webpay_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("WEBPAY_API_KEY", "webpay_api_key"),
    )
    webpay_return_url: str = Field(
        default="",
        validation_alias=AliasChoices("WEBPAY_RETURN_URL", "webpay_return_url"),
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("FRONTEND_URL", "frontend_url"),
    )

    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "app_env"),
    )

    auth_rate_limit_max: int = Field(
        default=10,
        validation_alias=AliasChoices("AUTH_RATE_LIMIT_MAX", "auth_rate_limit_max"),
        description="Maximo de solicitudes POST /auth/login|register por IP en la ventana.",
    )
    auth_rate_limit_window_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "AUTH_RATE_LIMIT_WINDOW_SECONDS",
            "auth_rate_limit_window_seconds",
        ),
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def _normalize_app_env(cls, value: object) -> str:
        if value is None:
            return "development"
        text = str(value).strip().lower()
        return text or "development"

    @field_validator("auth_rate_limit_max", "auth_rate_limit_window_seconds", mode="before")
    @classmethod
    def _coerce_positive_int(cls, value: object) -> int:
        if value is None or value == "":
            return 0
        return int(value)

    @field_validator("auth_rate_limit_max")
    @classmethod
    def _validate_rate_limit_max(cls, value: int) -> int:
        return max(1, value)

    @field_validator("auth_rate_limit_window_seconds")
    @classmethod
    def _validate_rate_limit_window(cls, value: int) -> int:
        return max(1, value)

    def is_production(self) -> bool:
        return self.app_env == "production"

    def cors_allow_origins(self) -> list[str]:
        if self.is_production():
            origin = self.frontend_url.rstrip("/")
            return [origin] if origin else []
        return ["*"]

    def debug_routes_enabled(self) -> bool:
        return not self.is_production()

    @field_validator(
        "webpay_commerce_code",
        "webpay_api_key",
        "webpay_return_url",
        "frontend_url",
        mode="before",
    )
    @classmethod
    def _strip_webpay_strings(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip().strip('"').strip("'")

    def webpay_configured(self) -> bool:
        return bool(
            self.webpay_commerce_code.strip()
            and self.webpay_api_key.strip()
            and self.webpay_return_url.strip()
        )


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de Settings (caché por proceso)."""
    return Settings()
