import logging
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app.api.deps.auth import get_optional_current_user
from app.config import Settings, get_settings
from app.schemas.auth import UserPublic
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
    current_user: UserPublic | None = Depends(get_optional_current_user),
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
        "GET /acca risk=%s user_id=%s requested_date=%s resolved_date=%s",
        risk,
        current_user.id if current_user else None,
        requested_day.isoformat(),
        resolved_day.isoformat(),
    )

    try:
        result = generate_acca_for_date(settings, resolved_day, risk, fetch_odds=fetch_odds)
    except Exception as exc:
        logger.exception(
            "DIAG GET /acca generate falló risk=%s date=%s error=%s: %s",
            risk,
            resolved_day.isoformat(),
            type(exc).__name__,
            exc,
        )
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

    meta = result.get("meta") or {}
    if int(result.get("pick_count") or 0) == 0:
        logger.warning(
            "DIAG GET /acca sin picks risk=%s date=%s upstream_fixtures=%s "
            "after_schedule=%s pool=%s eligible=%s message=%s",
            risk,
            resolved_day.isoformat(),
            meta.get("fixtures_upstream_total"),
            meta.get("fixtures_after_schedule_filter"),
            meta.get("candidates_pool_size"),
            meta.get("eligible_after_filters"),
            result.get("message"),
        )

    profile = result.get("profile") or {}
    min_required = int(profile.get("min_picks") or 0)
    if result["pick_count"] < min_required and risk != "extreme":
        result["message"] = (
            result.get("message")
            or "No hay suficientes partidos disponibles actualmente para armar esta combinada."
        )

    try:
        acca_id, persist_detail = persist_smart_acca(
            settings,
            result,
            user_id=current_user.id if current_user else None,
        )
        if acca_id:
            result["acca_id"] = acca_id
            result["meta"]["persist_status"] = "ok"
            result["meta"]["persist_error"] = None
        elif persist_detail in (
            "no_database_url",
            "no_sqlalchemy_impl_or_disabled",
            "no_picks_to_persist",
        ):
            result["meta"]["persist_status"] = "skipped"
            result["meta"]["persist_error"] = None
        elif persist_detail == "login_required":
            result["meta"]["persist_status"] = "skipped"
            result["meta"]["persist_error"] = "login_required"
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


_HISTORY_UNAVAILABLE_MSG = "No hay historial disponible."


@router.get("/history", response_model=AccaHistoryListResponse)
def get_acca_history(
    limit: int = Query(default=30, ge=1, le=200),
    settings: Settings = Depends(get_settings),
    current_user: UserPublic | None = Depends(get_optional_current_user),
) -> AccaHistoryListResponse:
    """Historial de combinadas guardadas del usuario autenticado."""
    configured = database_connected(settings, try_migrate=False)
    db_message: str | None = None
    requires_auth = False
    items = []

    if not configured:
        db_message = database_status_message(settings) or _HISTORY_UNAVAILABLE_MSG
    elif current_user is None:
        requires_auth = True
        db_message = "Inicia sesión para ver tu historial de combinadas."
    else:
        try:
            logger.info("GET /acca/history user_id=%s limit=%s", current_user.id, limit)
            items = list_acca_history(settings, limit=limit, user_id=current_user.id)
        except Exception:
            logger.exception("GET /acca/history: error inesperado")
            items = []

    return AccaHistoryListResponse(
        items=items,
        database_configured=configured,
        database_message=db_message,
        requires_auth=requires_auth,
    )
