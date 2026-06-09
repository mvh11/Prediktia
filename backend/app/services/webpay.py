"""Cliente HTTP para Transbank Webpay Plus (REST v1.2)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.config import Settings

logger = logging.getLogger(__name__)

_INTEGRATION_BASE = "https://webpay3gint.transbank.cl/rswebpaytransaction/api/webpay/v1.2"
_PRODUCTION_BASE = "https://webpay3g.transbank.cl/rswebpaytransaction/api/webpay/v1.2"


class WebpayError(Exception):
    """Error al comunicarse con Transbank."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def webpay_api_base(settings: Settings) -> str:
    env = (settings.webpay_env or "integration").strip().lower()
    if env in ("production", "prod", "live"):
        return _PRODUCTION_BASE
    return _INTEGRATION_BASE


def _auth_headers(settings: Settings) -> dict[str, str]:
    return {
        "Tbk-Api-Key-Id": settings.webpay_commerce_code,
        "Tbk-Api-Key-Secret": settings.webpay_api_key,
        "Content-Type": "application/json",
    }


def create_webpay_transaction(
    settings: Settings,
    *,
    buy_order: str,
    session_id: str,
    amount: int,
    return_url: str,
) -> dict[str, Any]:
    """POST /transactions — crea transacción Webpay Plus."""
    url = f"{webpay_api_base(settings)}/transactions"
    payload = {
        "buy_order": buy_order,
        "session_id": session_id,
        "amount": amount,
        "return_url": return_url,
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=_auth_headers(settings),
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning("Webpay create: error de red — %s", exc)
        raise WebpayError("No se pudo conectar con Transbank.") from exc

    if not resp.ok:
        logger.warning(
            "Webpay create HTTP %s body=%s",
            resp.status_code,
            resp.text[:500],
        )
        raise WebpayError(
            f"Transbank rechazó la creación (HTTP {resp.status_code}).",
            status_code=resp.status_code,
        )

    data = resp.json()
    token = data.get("token")
    pay_url = data.get("url")
    if not token or not pay_url:
        raise WebpayError("Respuesta incompleta de Transbank (sin url/token).")
    return {"token": str(token), "url": str(pay_url)}


def commit_webpay_transaction(settings: Settings, token: str) -> dict[str, Any]:
    """PUT /transactions/{token} — confirma transacción."""
    url = f"{webpay_api_base(settings)}/transactions/{token}"
    try:
        resp = requests.put(
            url,
            headers=_auth_headers(settings),
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning("Webpay commit: error de red — %s", exc)
        raise WebpayError("No se pudo confirmar el pago con Transbank.") from exc

    if not resp.ok:
        logger.warning(
            "Webpay commit HTTP %s token=%s… body=%s",
            resp.status_code,
            token[:12],
            resp.text[:500],
        )
        raise WebpayError(
            f"Transbank rechazó la confirmación (HTTP {resp.status_code}).",
            status_code=resp.status_code,
        )

    return resp.json()
