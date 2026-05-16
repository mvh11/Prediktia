"""
Endpoint temporal de diagnóstico LATAM (fixtures, odds upstream, mock EV, filtros).
"""

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.schemas.latam_debug import LatamDebugResponse
from app.services.acca_persistence import fetch_acca_db_last_debug
from app.services.acca_fixture_filter import build_acca_filter_debug_report, build_acca_filter_raw_rows
from app.services.football_api import FootballApiError, fetch_fixtures_by_date_cached
from app.services.pipeline_debug import build_latam_debug_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/acca-db-last")
def debug_acca_db_last(settings: Settings = Depends(get_settings)) -> dict:
    """Última ACCA y prediction en DB + conteos (misma DATABASE_URL que persistencia)."""
    logger.info("GET /debug/acca-db-last")
    return fetch_acca_db_last_debug(settings)


def _parse_date(value: str | None) -> date:
    if not value:
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Parámetro 'date' inválido. Usa formato YYYY-MM-DD (día UTC).",
        ) from exc


@router.get("/latam", response_model=LatamDebugResponse)
def debug_latam_pipeline(
    date_param: str | None = Query(
        default=None,
        alias="date",
        description="Día UTC para GET /fixtures (igual que /matches).",
    ),
    fetch_odds: bool = Query(
        default=True,
        description="Si true, llama GET /odds?fixture= por cada fixture LATAM (consume cuota API).",
    ),
    settings: Settings = Depends(get_settings),
) -> LatamDebugResponse:
    """
    Trazado completo del pipeline para Chile, Brasil, Argentina y resto LATAM.

  Descubre en qué etapa desaparecen partidos: fixtures del día UTC, odds reales,
  picks mock EV, y pistas de filtros solo-frontend (tier D, editorial).
    """
    day = _parse_date(date_param)
    logger.info(
        "GET /debug/latam date=%s fetch_odds=%s",
        day.isoformat(),
        fetch_odds,
    )
    try:
        report = build_latam_debug_report(settings, day, fetch_odds=fetch_odds)
    except FootballApiError as exc:
        logger.error("debug/latam upstream error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return LatamDebugResponse.model_validate(report)


@router.get("/acca-filter")
def debug_acca_filter(
    date_param: str | None = Query(
        default=None,
        alias="date",
        description="Día UTC para GET /fixtures (igual que /acca).",
    ),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Diagnóstico del filtro temporal/estado ACCA (misma lógica que el builder).
    """
    day = _parse_date(date_param)
    logger.info("GET /debug/acca-filter date=%s", day.isoformat())
    try:
        payload = fetch_fixtures_by_date_cached(settings, day)
    except FootballApiError as exc:
        logger.error("debug/acca-filter upstream error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    fixtures = payload.get("response") or []
    if not isinstance(fixtures, list):
        fixtures = []

    return build_acca_filter_debug_report(
        fixtures,
        min_minutes_before_kickoff=settings.acca_min_minutes_before_kickoff,
    )


@router.get("/acca-filter/raw")
def debug_acca_filter_raw(
    date_param: str | None = Query(
        default=None,
        alias="date",
        description="Día UTC para GET /fixtures (igual que /acca).",
    ),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Primeros 20 fixtures: timestamp/date crudos vs UTC now y decisión del filtro."""
    day = _parse_date(date_param)
    logger.info("GET /debug/acca-filter/raw date=%s", day.isoformat())
    try:
        payload = fetch_fixtures_by_date_cached(settings, day)
    except FootballApiError as exc:
        logger.error("debug/acca-filter/raw upstream error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    fixtures = payload.get("response") or []
    if not isinstance(fixtures, list):
        fixtures = []

    return build_acca_filter_raw_rows(
        fixtures,
        min_minutes_before_kickoff=settings.acca_min_minutes_before_kickoff,
    )
