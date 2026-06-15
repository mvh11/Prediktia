"""Pagos Webpay Plus — creación y retorno."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps.auth import get_current_user
from app.config import Settings, get_settings
from app.db.session import session_scope
from app.schemas.auth import UserPublic
from app.schemas.payments import (
    CreateWebpayPaymentRequest,
    CreateWebpayPaymentResponse,
    PaymentHistoryItem,
    PaymentHistoryListResponse,
)
from app.services.payments import (
    PAYMENT_STATUS_APPROVED,
    PAYMENT_STATUS_REJECTED,
    attach_webpay_token,
    create_pending_payment,
    get_payment_by_buy_order,
    get_payment_by_token,
    list_user_payments,
    set_payment_status,
)
from app.services.plan_permissions import can_use_full_value_bets, normalize_tier
from app.services.users import update_user_tier
from app.services.webpay import WebpayError, commit_webpay_transaction, create_webpay_transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])

PLAN_AMOUNTS: dict[str, int] = {
    "premium": 4990,
}


def _require_database(settings: Settings) -> str:
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pagos requieren DATABASE_URL (PostgreSQL).",
        )
    return settings.database_url


def _require_webpay(settings: Settings) -> None:
    if not settings.webpay_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webpay no está configurado en el servidor.",
        )


def _frontend_plans_url(settings: Settings, payment: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/planes?payment={payment}"


def _make_buy_order(user_id: int) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    raw = f"P{user_id}{ts}"
    return raw[:26]


def _make_session_id(user_id: int) -> str:
    return f"u{user_id}-{uuid.uuid4().hex}"[:61]


async def _extract_token_ws(request: Request) -> str | None:
    token = request.query_params.get("token_ws")
    if token:
        return str(token).strip() or None
    if request.method == "POST":
        try:
            form = await request.form()
            form_token = form.get("token_ws")
            if form_token:
                return str(form_token).strip() or None
        except Exception:
            logger.debug("webpay return: no se pudo leer form", exc_info=True)
    return None


@router.get("/history", response_model=PaymentHistoryListResponse)
def payment_history(
    limit: int = 20,
    settings: Settings = Depends(get_settings),
    current_user: UserPublic = Depends(get_current_user),
) -> PaymentHistoryListResponse:
    """Historial de pagos del usuario autenticado."""
    database_url = _require_database(settings)

    with session_scope(database_url) as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible.",
            )

        rows = list_user_payments(session, current_user.id, limit=limit)
        items = [
            PaymentHistoryItem(
                id=row.id,
                plan=row.plan,
                amount=row.amount,
                status=row.status,  # type: ignore[arg-type]
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ]

    return PaymentHistoryListResponse(items=items)


@router.post("/webpay/create", response_model=CreateWebpayPaymentResponse)
def create_webpay_payment(
    body: CreateWebpayPaymentRequest,
    settings: Settings = Depends(get_settings),
    current_user: UserPublic = Depends(get_current_user),
) -> CreateWebpayPaymentResponse:
    """Crea transacción Webpay Plus para el plan indicado (usuario autenticado)."""
    _require_webpay(settings)
    database_url = _require_database(settings)

    plan = body.plan
    amount = PLAN_AMOUNTS.get(plan)
    if amount is None:
        raise HTTPException(status_code=400, detail="Plan no disponible para pago.")

    user_tier = normalize_tier(current_user.tier)
    if can_use_full_value_bets(user_tier) and plan == "premium":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tienes acceso Premium activo.",
        )

    buy_order = _make_buy_order(current_user.id)
    session_id = _make_session_id(current_user.id)
    return_url = settings.webpay_return_url.rstrip("/")

    with session_scope(database_url) as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible.",
            )

        payment = create_pending_payment(
            session,
            user_id=current_user.id,
            plan=plan,
            amount=amount,
            buy_order=buy_order,
            session_id=session_id,
        )

        try:
            tx = create_webpay_transaction(
                settings,
                buy_order=buy_order,
                session_id=session_id,
                amount=amount,
                return_url=return_url,
            )
        except WebpayError as exc:
            set_payment_status(session, payment, PAYMENT_STATUS_REJECTED)
            logger.warning(
                "Webpay create falló user_id=%s buy_order=%s — %s",
                current_user.id,
                buy_order,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        attach_webpay_token(session, payment, tx["token"])
        logger.info(
            "Webpay create OK user_id=%s payment_id=%s buy_order=%s amount=%s",
            current_user.id,
            payment.id,
            buy_order,
            amount,
        )

    return CreateWebpayPaymentResponse(url=tx["url"], token=tx["token"])


@router.api_route("/webpay/return", methods=["GET", "POST"], include_in_schema=False)
async def webpay_return(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """
    Callback de Webpay: confirma transacción y redirige al frontend.
    Webpay envía token_ws por GET (v1.1+) o POST según flujo/ambiente.
    """
    _require_webpay(settings)
    database_url = _require_database(settings)

    token_ws = await _extract_token_ws(request)
    if not token_ws:
        logger.info("Webpay return sin token_ws — pago abortado o cancelado")
        return RedirectResponse(_frontend_plans_url(settings, "failed"), status_code=303)

    try:
        commit = commit_webpay_transaction(settings, token_ws)
    except WebpayError as exc:
        logger.warning("Webpay commit falló token=%s… — %s", token_ws[:12], exc)
        return RedirectResponse(_frontend_plans_url(settings, "failed"), status_code=303)

    response_code = commit.get("response_code")
    buy_order = commit.get("buy_order")
    approved = response_code == 0

    logger.info(
        "Webpay commit token=%s… buy_order=%s response_code=%s approved=%s",
        token_ws[:12],
        buy_order,
        response_code,
        approved,
    )

    with session_scope(database_url) as session:
        if session is None:
            return RedirectResponse(_frontend_plans_url(settings, "failed"), status_code=303)

        payment = get_payment_by_token(session, token_ws)
        if payment is None and buy_order:
            payment = get_payment_by_buy_order(session, str(buy_order))

        if payment is None:
            logger.warning("Webpay return: payment no encontrado token=%s…", token_ws[:12])
            return RedirectResponse(_frontend_plans_url(settings, "failed"), status_code=303)

        if approved:
            set_payment_status(session, payment, PAYMENT_STATUS_APPROVED)
            if payment.plan == "premium":
                update_user_tier(session, payment.user_id, "premium")
            logger.info(
                "Pago aprobado payment_id=%s user_id=%s plan=%s",
                payment.id,
                payment.user_id,
                payment.plan,
            )
            return RedirectResponse(_frontend_plans_url(settings, "success"), status_code=303)

        set_payment_status(session, payment, PAYMENT_STATUS_REJECTED)
        logger.info(
            "Pago rechazado payment_id=%s user_id=%s response_code=%s",
            payment.id,
            payment.user_id,
            response_code,
        )
        return RedirectResponse(_frontend_plans_url(settings, "failed"), status_code=303)
