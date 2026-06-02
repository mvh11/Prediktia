"""
Cliente API-Football con caché en memoria, singleflight y fallback ante rate limit (429).

- Fixtures: una entrada por fecha, TTL ≥ 5 min, reutilizada por /matches, /value-bets y /acca.
- Odds: caché por fixture_id con el mismo TTL.
- 429 / error de red: devuelve caché antigua o lista vacía (nunca obliga al caller a propagar 502).
"""

from __future__ import annotations

import copy
import logging
import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

from app.config import Settings

logger = logging.getLogger(__name__)

CACHE_META_KEY = "_prediktia_cache"

# Fixtures por fecha ISO
_cache_lock = threading.Lock()
_fixtures_cache: dict[str, dict[str, Any]] = {}
_fixtures_cache_ts: dict[str, float] = {}

# Odds por fixture_id
_odds_cache: dict[int, dict[str, Any]] = {}
_odds_cache_ts: dict[int, float] = {}

# Singleflight: una petición HTTP en vuelo por clave
_sf_lock = threading.Lock()
_sf_fixtures: dict[str, threading.Event] = {}
_sf_fixtures_result: dict[str, dict[str, Any]] = {}
_sf_odds: dict[int, threading.Event] = {}
_sf_odds_result: dict[int, dict[str, Any]] = {}


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


@dataclass(frozen=True)
class CacheMeta:
    cache_hit: bool = False
    stale: bool = False
    rate_limited: bool = False
    warning: str | None = None


def _effective_ttl_seconds(settings: Settings) -> int:
    raw = int(settings.matches_upstream_cache_ttl_seconds or 0)
    return max(300, raw) if raw != 0 else 300


def _is_rate_limited(exc: FootballApiError) -> bool:
    if exc.status_code == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg or "too many request" in msg or "rate limit" in msg


def _empty_fixtures_payload() -> dict[str, Any]:
    return {"response": [], "results": 0}


def _attach_meta(payload: dict[str, Any], meta: CacheMeta) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    out[CACHE_META_KEY] = {
        "cache_hit": meta.cache_hit,
        "stale": meta.stale,
        "rate_limited": meta.rate_limited,
        "warning": meta.warning,
    }
    return out


def extract_cache_meta(payload: dict[str, Any]) -> CacheMeta:
    raw = payload.get(CACHE_META_KEY)
    if not isinstance(raw, dict):
        return CacheMeta()
    return CacheMeta(
        cache_hit=bool(raw.get("cache_hit")),
        stale=bool(raw.get("stale")),
        rate_limited=bool(raw.get("rate_limited")),
        warning=raw.get("warning") if isinstance(raw.get("warning"), str) else None,
    )


def peek_fixtures_cache(day: date) -> dict[str, Any] | None:
    """Devuelve fixtures cacheados (frescos o viejos) sin llamar al upstream."""
    key = day.isoformat()
    with _cache_lock:
        if key in _fixtures_cache:
            return copy.deepcopy(_fixtures_cache[key])
    return None


def _store_fixtures(key: str, payload: dict[str, Any]) -> None:
    with _cache_lock:
        _fixtures_cache[key] = copy.deepcopy(payload)
        _fixtures_cache_ts[key] = time.monotonic()


def _get_fresh_fixtures(key: str, ttl: int) -> dict[str, Any] | None:
    now = time.monotonic()
    with _cache_lock:
        if key not in _fixtures_cache:
            return None
        age = now - _fixtures_cache_ts.get(key, 0.0)
        if age < ttl:
            return copy.deepcopy(_fixtures_cache[key])
    return None


def _get_stale_fixtures(key: str) -> dict[str, Any] | None:
    with _cache_lock:
        if key in _fixtures_cache:
            return copy.deepcopy(_fixtures_cache[key])
    return None


def _api_key_present(settings: Settings) -> bool:
    return bool((settings.api_football_key or "").strip())


def _api_get(
    settings: Settings,
    path: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    base = (settings.api_football_base_url or "https://v3.football.api-sports.io").rstrip("/")
    url = f"{base}/{path.lstrip('/')}"
    api_key = (settings.api_football_key or "").strip()
    key_present = bool(api_key)

    # API-Sports directo (NO RapidAPI): solo x-apisports-key
    headers = {
        "x-apisports-key": api_key,
        "Accept": "application/json",
    }
    timeout = (
        settings.api_football_timeout_connect_seconds,
        settings.api_football_timeout_read_seconds,
    )

    logger.info(
        "API-Football request key_present=%s base_url=%s endpoint=%s params=%s",
        key_present,
        base,
        url,
        params,
    )

    if not key_present:
        raise FootballApiError(
            "API_FOOTBALL_KEY vacía: define la variable en Render (Environment).",
            status_code=None,
            response_text=None,
        )

    try:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        logger.error(
            "API-Football connection error endpoint=%s key_present=%s error=%s",
            url,
            key_present,
            exc,
        )
        raise FootballApiError(
            f"No se pudo conectar con API-Football: {exc}",
            status_code=None,
            response_text=None,
        ) from exc

    body_preview = response.text[:4000] if response.text else ""

    if response.status_code != 200:
        logger.error(
            "API-Football HTTP error status_code=%s endpoint=%s key_present=%s body=%s",
            response.status_code,
            url,
            key_present,
            body_preview[:800],
        )
        raise FootballApiError(
            f"API-Football respondió {response.status_code}: {response.text[:500]}",
            status_code=response.status_code,
            response_text=body_preview or None,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        logger.error(
            "API-Football invalid JSON status_code=%s endpoint=%s body=%s",
            response.status_code,
            url,
            body_preview[:800],
        )
        raise FootballApiError(
            "La respuesta no es JSON válido.",
            status_code=response.status_code,
            response_text=body_preview or None,
        ) from exc

    errors = payload.get("errors")
    if errors:
        logger.error(
            "API-Football API errors endpoint=%s errors=%s body=%s",
            url,
            errors,
            body_preview[:800],
        )
        raise FootballApiError(
            f"API-Football devolvió errores: {errors}",
            status_code=response.status_code,
            response_text=body_preview or None,
        )

    logger.info(
        "API-Football OK status_code=%s endpoint=%s results=%s",
        response.status_code,
        url,
        payload.get("results"),
    )
    return payload


def fetch_fixtures_by_date(settings: Settings, day: date) -> dict[str, Any]:
    """GET /fixtures?date=YYYY-MM-DD (sin caché; puede lanzar FootballApiError)."""
    return _api_get(settings, "fixtures", {"date": day.isoformat()})


def _fetch_fixtures_upstream_once(settings: Settings, day: date) -> dict[str, Any]:
    key = day.isoformat()
    ttl = _effective_ttl_seconds(settings)

    fresh = _get_fresh_fixtures(key, ttl)
    if fresh is not None:
        logger.debug("fixtures cache HIT fresh date=%s", key)
        return _attach_meta(fresh, CacheMeta(cache_hit=True))

    with _sf_lock:
        if key in _sf_fixtures:
            waiter = True
            event = _sf_fixtures[key]
        else:
            waiter = False
            event = threading.Event()
            _sf_fixtures[key] = event

    if waiter:
        event.wait(timeout=90.0)
        with _sf_lock:
            result = copy.deepcopy(_sf_fixtures_result.get(key, _empty_fixtures_payload()))
        return result

    result_payload: dict[str, Any]
    try:
        try:
            payload = fetch_fixtures_by_date(settings, day)
            if not isinstance(payload.get("response"), list):
                payload = {**payload, "response": payload.get("response") or []}
            _store_fixtures(key, payload)
            logger.info("fixtures upstream OK date=%s count=%s", key, len(payload.get("response") or []))
            result_payload = _attach_meta(payload, CacheMeta(cache_hit=False))
        except FootballApiError as exc:
            logger.error(
                "DIAG fixtures upstream FAILED date=%s key_present=%s base_url=%s "
                "status_code=%s error=%s response_body=%s",
                key,
                _api_key_present(settings),
                settings.api_football_base_url,
                exc.status_code,
                exc,
                (exc.response_text or "")[:800],
            )
            stale = _get_stale_fixtures(key)
            if stale is not None:
                warn = (
                    "Datos en caché (API-Football no disponible temporalmente). "
                    f"Detalle: {exc}"
                )
                logger.warning("fixtures upstream error date=%s — using STALE cache: %s", key, exc)
                result_payload = _attach_meta(
                    stale,
                    CacheMeta(stale=True, rate_limited=_is_rate_limited(exc), warning=warn),
                )
            else:
                warn = (
                    "API-Football no disponible y sin caché previa. "
                    f"Detalle: {exc}"
                )
                logger.warning(
                    "fixtures upstream error date=%s — empty fallback (ver log ERROR anterior)",
                    key,
                )
                result_payload = _attach_meta(
                    _empty_fixtures_payload(),
                    CacheMeta(rate_limited=_is_rate_limited(exc), warning=warn),
                )
    finally:
        with _sf_lock:
            _sf_fixtures_result[key] = result_payload
            ev = _sf_fixtures.pop(key, None)
            if ev is not None:
                ev.set()

    return result_payload


def fetch_fixtures_by_date_cached(settings: Settings, day: date) -> dict[str, Any]:
    """
    Fixtures del día con caché compartida (matches / value / acca).
    No lanza excepción: ante 429 usa caché antigua o [].
    """
    return _fetch_fixtures_upstream_once(settings, day)


def fetch_fixtures_by_ids(settings: Settings, fixture_ids: list[int]) -> dict[str, Any]:
    """GET /fixtures?ids=… (troceado). Sin caché dedicada; uso puntual."""
    ids = sorted({int(i) for i in fixture_ids if i is not None})
    if not ids:
        return {"response": []}
    chunk_size = 20
    merged: list[dict[str, Any]] = []
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        ids_param = "-".join(str(x) for x in chunk)
        try:
            payload = _api_get(settings, "fixtures", {"ids": ids_param})
        except FootballApiError as exc:
            logger.warning("fetch_fixtures_by_ids chunk failed: %s", exc)
            continue
        part = payload.get("response") or []
        if isinstance(part, list):
            merged.extend(p for p in part if isinstance(p, dict))
    return {"response": merged}


def _store_odds(fid: int, payload: dict[str, Any]) -> None:
    with _cache_lock:
        _odds_cache[fid] = copy.deepcopy(payload)
        _odds_cache_ts[fid] = time.monotonic()


def _get_fresh_odds(fid: int, ttl: int) -> dict[str, Any] | None:
    now = time.monotonic()
    with _cache_lock:
        if fid not in _odds_cache:
            return None
        if now - _odds_cache_ts.get(fid, 0.0) < ttl:
            return copy.deepcopy(_odds_cache[fid])
    return None


def _get_stale_odds(fid: int) -> dict[str, Any] | None:
    with _cache_lock:
        if fid in _odds_cache:
            return copy.deepcopy(_odds_cache[fid])
    return None


def fetch_odds_by_fixture(settings: Settings, fixture_id: int) -> dict[str, Any]:
    """GET /odds?fixture={id} (sin caché; puede lanzar)."""
    return _api_get(settings, "odds", {"fixture": fixture_id})


def fetch_odds_by_fixture_cached(settings: Settings, fixture_id: int) -> dict[str, Any]:
    """Cuotas por fixture con caché; no lanza (devuelve {{response: []}} si falla)."""
    fid = int(fixture_id)
    ttl = _effective_ttl_seconds(settings)

    fresh = _get_fresh_odds(fid, ttl)
    if fresh is not None:
        return fresh

    with _sf_lock:
        if fid in _sf_odds:
            event = _sf_odds[fid]
            waiter = True
        else:
            waiter = False
            event = threading.Event()
            _sf_odds[fid] = event

    if waiter:
        event.wait(timeout=60.0)
        with _sf_lock:
            return copy.deepcopy(_sf_odds_result.get(fid, {"response": []}))

    try:
        payload = fetch_odds_by_fixture(settings, fid)
        _store_odds(fid, payload)
        result = payload
    except FootballApiError as exc:
        stale = _get_stale_odds(fid)
        if stale is not None:
            logger.debug("odds STALE fixture=%s: %s", fid, exc)
            result = stale
        else:
            logger.debug("odds empty fixture=%s: %s", fid, exc)
            result = {"response": []}
    finally:
        with _sf_lock:
            _sf_odds_result[fid] = result
            ev = _sf_odds.pop(fid, None)
            if ev is not None:
                ev.set()

    return result
