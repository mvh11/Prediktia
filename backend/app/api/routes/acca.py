import logging
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas.acca import AccaHistoryListResponse, SmartAccaResponse
from app.services.acca_persistence import list_acca_history, persist_smart_acca
from app.services.db_health import database_connected, database_status_message
from app.services.smart_acca import (
    RiskLevel,
    SIMPLE_PROFILES,
    RISK_LABELS,
    generate_acca_for_date,
    resolve_acca_calendar_day_for_pre_match,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/acca", tags=["acca"])


def _safe_empty_acca(day: date, risk: RiskLevel, message: str) -> dict[str, Any]:
    profile = SIMPLE_PROFILES[risk]
    n = profile.exact_picks
    return {
        "date": day.isoformat(),
        "model_version": "poisson-v1+ev-simple",
        "risk": risk,
        "risk_label": RISK_LABELS[risk],
        "profile": {
            "min_picks": n,
            "max_picks": n,
            "target_odds_range": f"{profile.target_min} – {profile.target_max}",
        },
        "picks": [],
        "pick_count": 0,
        "total_odds": 1.0,
        "combined_probability": 0.0,
        "combined_ev": 0.0,
        "combined_ev_pct": 0.0,
        "confidence_score": 0.0,
        "risk_score": 0.0,
        "volatility_score": 0.0,
        "message": message,
        "meta": {
            "candidates_pool_size": 0,
            "eligible_after_filters": 0,
            "bookmaker_odds_picks": 0,
            "independence_assumption": "P(combinada) ≈ ∏ P(picks).",
            "fetch_odds": False,
            "fixtures_upstream_total": 0,
            "fixtures_after_schedule_filter": 0,
            "fixtures_after_schedule_strict": 0,
            "schedule_filter_fallback": False,
            "schedule_discard_reasons": {},
            "fixtures_source": "api_football",
            "requested_date": day.isoformat(),
            "resolved_date": day.isoformat(),
            "auto_shifted_date": False,
            "unique_fixtures_count": 0,
            "risk_profile_validation": {},
            "persist_status": "not_attempted",
            "persist_error": None,
        },
    }


def _parse_date_required(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Parámetro 'date' inválido. Usa formato YYYY-MM-DD (UTC).",
        ) from exc


@router.get("", response_model=SmartAccaResponse)
def get_smart_acca(
    risk: RiskLevel = Query(
        default="medium",
        description="Perfil: low (Bajo), medium (Medio), high (Alto), extreme (Muy alto).",
    ),
    date_param: str | None = Query(
        default=None,
        alias="date",
        description="Fecha UTC (YYYY-MM-DD). Si se omite, se busca el primer día en [hoy..hoy+3] con fixtures pre-partido válidos.",
    ),
    fetch_odds: bool = Query(
        default=False,
        description="Enriquecer con cuotas API-Football (costoso; desactivado por defecto para el plan gratuito).",
    ),
    settings: Settings = Depends(get_settings),
) -> SmartAccaResponse:
    """Genera una combinada ACCA según el perfil de riesgo (motor simple Poisson + EV)."""
    requested_day: date
    resolved_day: date
    auto_shifted = False

    if date_param is None:
        requested_day = datetime.now(timezone.utc).date()
        resolved_day, _, auto_shifted = resolve_acca_calendar_day_for_pre_match(
            settings, requested_day, max_extra_days=1
        )
    else:
        requested_day = _parse_date_required(date_param)
        resolved_day = requested_day
        auto_shifted = False

    logger.info(
        "GET /acca risk=%s requested_date=%s resolved_date=%s",
        risk,
        requested_day.isoformat(),
        resolved_day.isoformat(),
    )

    try:
        result = generate_acca_for_date(settings, resolved_day, risk, fetch_odds=fetch_odds)
    except Exception:
        logger.exception("GET /acca: error inesperado risk=%s", risk)
        if risk == "extreme":
            result = _safe_empty_acca(
                resolved_day,
                risk,
                "No hay suficientes partidos disponibles actualmente para armar esta combinada.",
            )
        else:
            raise

    result["meta"]["requested_date"] = requested_day.isoformat()
    result["meta"]["resolved_date"] = resolved_day.isoformat()
    result["meta"]["auto_shifted_date"] = auto_shifted

    profile = result.get("profile") or {}
    min_required = int(profile.get("min_picks") or 0)
    if result["pick_count"] < min_required and risk != "extreme":
        result["message"] = (
            result.get("message")
            or "No hay suficientes partidos disponibles actualmente para armar esta combinada."
        )

    try:
        acca_id, persist_detail = persist_smart_acca(settings, result)
        if acca_id:
            result["acca_id"] = acca_id
            result["meta"]["persist_status"] = "ok"
            result["meta"]["persist_error"] = None
        elif persist_detail in ("no_database_url", "no_sqlalchemy_impl_or_disabled"):
            result["meta"]["persist_status"] = "skipped"
            result["meta"]["persist_error"] = None
        else:
            result["meta"]["persist_status"] = "failed"
            result["meta"]["persist_error"] = persist_detail
            logger.error("GET /acca persistencia fallida detail=%s", persist_detail)
    except Exception:
        logger.exception("GET /acca: excepción en persistencia")
        result["meta"]["persist_status"] = "failed"
        result["meta"]["persist_error"] = "unexpected_exception_in_route"

    try:
        return SmartAccaResponse.model_validate(result)
    except ValidationError:
        logger.exception("GET /acca: respuesta no validó schema; devolviendo vacío risk=%s", risk)
        empty = _safe_empty_acca(
            resolved_day,
            risk,
            "No hay suficientes partidos disponibles actualmente para armar esta combinada.",
        )
        empty["meta"]["requested_date"] = requested_day.isoformat()
        empty["meta"]["resolved_date"] = resolved_day.isoformat()
        empty["meta"]["auto_shifted_date"] = auto_shifted
        return SmartAccaResponse.model_validate(empty)


@router.get("/history", response_model=AccaHistoryListResponse)
def get_acca_history(
    limit: int = Query(default=30, ge=1, le=200),
    settings: Settings = Depends(get_settings),
) -> AccaHistoryListResponse:
    """Historial de combinadas guardadas (PostgreSQL / Neon)."""
    configured = database_connected(settings, try_migrate=True)
    db_message: str | None = None
    if not configured:
        db_message = database_status_message(settings)

    try:
        items = list_acca_history(settings, limit=limit)
    except Exception:
        logger.exception("GET /acca/history: error inesperado")
        items = []

    if configured and not db_message:
        configured = database_connected(settings)

    return AccaHistoryListResponse(
        items=items,
        database_configured=configured,
        database_message=db_message,
    )
