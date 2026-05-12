import logging
import threading
import time
from datetime import date
from typing import Any

import requests

from app.config import Settings

logger = logging.getLogger(__name__)

# Caché en memoria: una entrada por fecha (última respuesta OK del upstream).
_cache_lock = threading.Lock()
_fixtures_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class FootballApiError(Exception):
    """Error al llamar a API-Football o al interpretar la respuesta."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


def fetch_fixtures_by_date(settings: Settings, day: date) -> dict[str, Any]:
    """
    Obtiene los partidos (fixtures) del día indicado.

    Una sola petición GET sin reintentos. Timeout (connect, read) desde settings.
    Documentación: GET /fixtures?date=YYYY-MM-DD.
    """
    url = f"{settings.api_football_base_url.rstrip('/')}/fixtures"
    headers = {"x-apisports-key": settings.api_football_key}
    params = {"date": day.isoformat()}
    timeout = (
        settings.api_football_timeout_connect_seconds,
        settings.api_football_timeout_read_seconds,
    )

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise FootballApiError(
            f"No se pudo conectar con API-Football: {exc}",
            status_code=None,
            response_text=None,
        ) from exc

    body_preview = response.text[:4000] if response.text else ""

    if response.status_code != 200:
        raise FootballApiError(
            f"API-Football respondió {response.status_code}: {response.text[:500]}",
            status_code=response.status_code,
            response_text=body_preview or None,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise FootballApiError(
            "La respuesta no es JSON válido.",
            status_code=response.status_code,
            response_text=body_preview or None,
        ) from exc

    errors = payload.get("errors")
    if errors:
        raise FootballApiError(
            f"API-Football devolvió errores: {errors}",
            status_code=response.status_code,
            response_text=body_preview or None,
        )

    return payload


def fetch_fixtures_by_date_cached(settings: Settings, day: date) -> dict[str, Any]:
    """
    Igual que fetch_fixtures_by_date pero reutiliza la última respuesta OK por fecha
    mientras no expire el TTL (sin peticiones extra al upstream en cache hit).
    """
    key = day.isoformat()
    ttl = settings.matches_upstream_cache_ttl_seconds
    if ttl > 0:
        now = time.monotonic()
        with _cache_lock:
            hit = _fixtures_cache.get(key)
            if hit:
                ts, cached = hit
                if now - ts < ttl:
                    logger.debug(
                        "Cache upstream /fixtures HIT date=%s age_s=%.2f ttl_s=%s",
                        key,
                        now - ts,
                        ttl,
                    )
                    return cached

    payload = fetch_fixtures_by_date(settings, day)

    if ttl > 0:
        with _cache_lock:
            _fixtures_cache[key] = (time.monotonic(), payload)

    return payload
