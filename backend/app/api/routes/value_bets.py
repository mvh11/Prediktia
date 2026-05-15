import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.schemas.value_bets import ValueBetPick, ValueBetsResponse
from app.services.football_api import FootballApiError, fetch_fixtures_by_date_cached
from app.services.value_bets import build_mock_positive_ev_picks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/value-bets", tags=["value-bets"])


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


@router.get("", response_model=ValueBetsResponse)
def list_value_bets(
    date_param: str | None = Query(
        default=None,
        alias="date",
        description="Misma semántica que /matches: fecha UTC YYYY-MM-DD.",
    ),
    settings: Settings = Depends(get_settings),
) -> ValueBetsResponse:
    """
    Picks con EV positivo derivados de los mismos fixtures que `/matches`.

    Reutiliza `fetch_fixtures_by_date_cached` (sin peticiones extra al upstream
    si la fecha ya está en caché por una llamada reciente a `/matches` o aquí).
    """
    day = _parse_date(date_param)
    try:
        payload = fetch_fixtures_by_date_cached(settings, day)
    except FootballApiError as exc:
        body_fragment = (exc.response_text or "")[:2000]
        logger.error(
            "Fallo upstream API-Football en value-bets. date=%s msg=%s http=%s body=%r",
            day.isoformat(),
            str(exc),
            exc.status_code,
            body_fragment,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    fixtures = payload.get("response") or []
    if not isinstance(fixtures, list):
        raise HTTPException(
            status_code=502,
            detail="Formato inesperado en la respuesta de API-Football.",
        )

    raw_picks = build_mock_positive_ev_picks(fixtures)
    picks = [ValueBetPick.model_validate(p) for p in raw_picks]

    return ValueBetsResponse(
        date=day.isoformat(),
        picks_count=len(picks),
        picks=picks,
    )
