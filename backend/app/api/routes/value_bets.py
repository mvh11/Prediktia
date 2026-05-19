import logging
import os
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.schemas.value_bets import ValueBetPick, ValueBetsResponse
from app.services.acca_fixture_filter import filter_and_sort_fixtures_for_acca
from app.services.football_api import extract_cache_meta, fetch_fixtures_by_date_cached
from app.services.pipeline_debug import log_all_fixtures_pipeline
from app.services.smart_acca import resolve_acca_calendar_day_for_pre_match
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
    Picks con EV positivo desde fixtures cacheados (misma caché que /matches y /acca).
    """
    warning: str | None = None
    stale = False

    if date_param is None:
        requested = datetime.now(timezone.utc).date()
        day, _, _ = resolve_acca_calendar_day_for_pre_match(
            settings, requested, max_extra_days=1
        )
    else:
        day = _parse_date(date_param)

    payload = fetch_fixtures_by_date_cached(settings, day)
    meta = extract_cache_meta(payload)
    if meta.warning:
        warning = meta.warning
    stale = meta.stale

    fixtures = payload.get("response") or []
    if not isinstance(fixtures, list):
        logger.warning("value-bets: response no es lista date=%s", day.isoformat())
        fixtures = []

    now_utc = datetime.now(timezone.utc)
    prematch_fixtures, _, _ = filter_and_sort_fixtures_for_acca(
        fixtures,
        now_utc=now_utc,
        min_minutes_before_kickoff=settings.acca_min_minutes_before_kickoff,
        emit_trace_log=False,
    )
    logger.info(
        "value-bets date=%s upstream=%s prematch=%s stale=%s",
        day.isoformat(),
        len(fixtures),
        len(prematch_fixtures),
        stale,
    )

    if len(fixtures) == 0:
        logger.warning(
            "DIAG GET /value-bets date=%s upstream_fixtures=0 warning=%s stale=%s "
            "(misma causa que /matches: API-Football vacía o 429)",
            day.isoformat(),
            warning,
            stale,
        )
    elif len(prematch_fixtures) == 0:
        logger.warning(
            "DIAG GET /value-bets date=%s prematch=0 upstream=%s "
            "(filtro horario eliminó todos; acca_min_minutes_before_kickoff=%s)",
            day.isoformat(),
            len(fixtures),
            settings.acca_min_minutes_before_kickoff,
        )

    raw_picks = build_mock_positive_ev_picks(prematch_fixtures)
    picks = [ValueBetPick.model_validate(p) for p in raw_picks]

    if len(picks) == 0:
        logger.warning(
            "DIAG GET /value-bets date=%s picks=0 prematch=%s "
            "(motor mock EV no generó picks para estos fixtures)",
            day.isoformat(),
            len(prematch_fixtures),
        )

    if os.environ.get("PIPELINE_DEBUG_LATAM", "").strip() in ("1", "true", "yes"):
        log_all_fixtures_pipeline(
            fixtures,
            settings,
            day,
            fetch_odds=False,
            latam_only=True,
        )

    return ValueBetsResponse(
        date=day.isoformat(),
        picks_count=len(picks),
        picks=picks,
        upstream_warning=warning,
        cache_stale=stale,
    )
