import logging
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.schemas.acca import (
    AccaHistoryListResponse,
    AccaSettleRequest,
    SmartAccaResponse,
)
from app.services.acca_persistence import (
    list_acca_history,
    persist_smart_acca,
    settle_acca_history,
)
from app.services.football_api import FootballApiError
from app.services.acca_settlement import settle_pending_accas
from app.services.smart_acca import (
    RiskLevel,
    generate_acca_for_date,
    resolve_acca_calendar_day_for_pre_match,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/acca", tags=["acca"])


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
        default=True,
        description="Enriquecer con cuotas API-Football cuando existan.",
    ),
    settings: Settings = Depends(get_settings),
) -> SmartAccaResponse:
    """
    Genera una combinada ACCA distinta según el perfil de riesgo.

    Motor: Poisson (probabilidades) + EV real vs cuota + selección anti-correlación.
    """
    requested_day: date
    resolved_day: date
    auto_shifted = False

    if date_param is None:
        requested_day = datetime.now(timezone.utc).date()
        resolved_day, _, auto_shifted = resolve_acca_calendar_day_for_pre_match(
            settings, requested_day
        )
    else:
        requested_day = _parse_date_required(date_param)
        resolved_day = requested_day

    logger.info(
        "GET /acca risk=%s requested_date=%s resolved_date=%s fetch_odds=%s",
        risk,
        requested_day.isoformat(),
        resolved_day.isoformat(),
        fetch_odds,
    )

    try:
        result = generate_acca_for_date(settings, resolved_day, risk, fetch_odds=fetch_odds)
    except FootballApiError as exc:
        logger.error("acca upstream error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    result["meta"]["requested_date"] = requested_day.isoformat()
    result["meta"]["resolved_date"] = resolved_day.isoformat()
    result["meta"]["auto_shifted_date"] = auto_shifted

    logger.info(
        "ACCA_DATE_RESOLVE requested=%s resolved=%s shifted=%s fixtures=%s",
        requested_day.isoformat(),
        resolved_day.isoformat(),
        str(auto_shifted).lower(),
        result["meta"].get("fixtures_after_schedule_filter", 0),
    )

    if result["pick_count"] == 0:
        result["message"] = (
            f"No se pudo armar combinada con los filtros de este riesgo para el día {result['date']} (UTC). "
            "Prueba otro perfil, otra fecha, o fetch_odds=true si hay cuotas en tu plan API."
        )

    try:
        acca_id, persist_detail = persist_smart_acca(settings, result)
        if acca_id:
            result["acca_id"] = acca_id
            result["meta"]["persist_status"] = "ok"
            result["meta"]["persist_error"] = None
            result["meta"]["persist_verify_message"] = persist_detail
            if persist_detail:
                logger.warning(
                    "GET /acca persist verify warning acca_id=%s detail=%s",
                    acca_id,
                    persist_detail,
                )
        elif persist_detail in ("no_database_url", "no_sqlalchemy_impl_or_disabled"):
            result["meta"]["persist_status"] = "skipped"
            result["meta"]["persist_error"] = None
            result["meta"]["persist_verify_message"] = persist_detail
        else:
            result["meta"]["persist_status"] = "failed"
            result["meta"]["persist_error"] = persist_detail
            result["meta"]["persist_verify_message"] = None
            logger.error("GET /acca persistencia fallida detail=%s", persist_detail)
    except Exception:
        logger.exception("GET /acca: excepción no esperada en persistencia")
        result["meta"]["persist_status"] = "failed"
        result["meta"]["persist_error"] = "unexpected_exception_in_route"
        result["meta"]["persist_verify_message"] = None

    return SmartAccaResponse.model_validate(result)


@router.get("/settle")
def run_acca_auto_settlement(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    """
    Ejecuta liquidación automática de ACCAs `pending` (resultados API-Football).
    Pensado para pruebas manuales; más adelante se puede invocar desde un scheduler.
    """
    if not settings.database_url:
        raise HTTPException(
            status_code=503,
            detail="Persistencia no disponible (sin DATABASE_URL).",
        )
    logger.info("GET /acca/settle manual trigger")
    return settle_pending_accas(settings)


@router.get("/history", response_model=AccaHistoryListResponse)
def get_acca_history(
    limit: int = Query(default=30, ge=1, le=200),
    settings: Settings = Depends(get_settings),
) -> AccaHistoryListResponse:
    """Historial de combinadas generadas (requiere DATABASE_URL + stack ORM)."""
    try:
        items = list_acca_history(settings, limit=limit)
    except Exception:
        logger.exception("GET /acca/history: error inesperado; se devuelve lista vacía.")
        items = []
    return AccaHistoryListResponse(
        items=items,
        database_configured=bool(settings.database_url),
    )


class AccaSettleResponse(BaseModel):
    acca_id: str
    status: str
    roi: float | None = None


@router.patch("/history/{acca_id}", response_model=AccaSettleResponse)
def patch_acca_history(
    acca_id: str,
    body: AccaSettleRequest,
    settings: Settings = Depends(get_settings),
) -> AccaSettleResponse:
    """Liquidación manual o vía job: pending | won | lost (+ ROI opcional)."""
    code = settle_acca_history(settings, acca_id, status=body.status, roi=body.roi)
    if code == "unavailable":
        raise HTTPException(
            status_code=503,
            detail="Persistencia no disponible (sin DATABASE_URL, sin SQLAlchemy o sin conexión).",
        )
    if code == "not_found":
        raise HTTPException(status_code=404, detail=f"No existe acca_id={acca_id}")
    if code == "error":
        raise HTTPException(status_code=500, detail="No se pudo actualizar la liquidación.")
    return AccaSettleResponse(acca_id=acca_id, status=body.status, roi=body.roi)
