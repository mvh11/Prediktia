import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.schemas.matches import MatchesResponse
from app.services.football_api import extract_cache_meta, fetch_fixtures_by_date_cached

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["matches"])


def _parse_date(value: str | None) -> date:
    if not value:
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Parámetro 'date' inválido. Usa formato YYYY-MM-DD.",
        ) from exc


@router.get("", response_model=MatchesResponse)
def list_matches(
    date_param: str | None = Query(
        default=None,
        alias="date",
        description="Fecha en YYYY-MM-DD. Si se omite, se usa la fecha UTC de hoy.",
    ),
    settings: Settings = Depends(get_settings),
) -> MatchesResponse:
    """
    Lista los partidos del día (por defecto hoy en UTC).

    Usa caché compartida de fixtures (TTL ≥ 5 min). Ante 429 devuelve caché antigua o [].
    """
    day = _parse_date(date_param)
    payload = fetch_fixtures_by_date_cached(settings, day)
    meta = extract_cache_meta(payload)

    fixtures = payload.get("response") or []
    if not isinstance(fixtures, list):
        logger.warning("matches: response no es lista date=%s", day.isoformat())
        fixtures = []

    if meta.rate_limited:
        logger.warning("matches: rate limit — stale=%s warning=%s", meta.stale, meta.warning)

    return MatchesResponse(
        date=day.isoformat(),
        results_count=len(fixtures),
        raw_fixtures=fixtures,
        upstream_warning=meta.warning,
        cache_stale=meta.stale,
    )
