import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.schemas.matches import MatchesResponse
from app.services.football_api import FootballApiError, fetch_fixtures_by_date_cached

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

    Los datos provienen de API-Football; se devuelve la lista en `raw_fixtures`
    para que el frontend pueda mapear los campos que necesite.
    """
    day = _parse_date(date_param)
    try:
        payload = fetch_fixtures_by_date_cached(settings, day)
    except FootballApiError as exc:
        body_fragment = (exc.response_text or "")[:2000]
        logger.error(
            "Fallo upstream API-Football (se responderá 502 al cliente). "
            "date=%s type=%s msg=%s http_status=%s body_fragment=%r",
            day.isoformat(),
            type(exc).__name__,
            str(exc),
            exc.status_code,
            body_fragment,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    fixtures = payload.get("response") or []
    if not isinstance(fixtures, list):
        logger.error(
            "Formato inesperado en payload API-Football (502). date=%s "
            "payload_keys=%s response_type=%s response_repr=%r",
            day.isoformat(),
            list(payload.keys()) if isinstance(payload, dict) else type(payload),
            type(fixtures).__name__,
            fixtures,
            exc_info=False,
        )
        raise HTTPException(
            status_code=502,
            detail="Formato inesperado en la respuesta de API-Football.",
        )

    return MatchesResponse(
        date=day.isoformat(),
        results_count=len(fixtures),
        raw_fixtures=fixtures,
    )
