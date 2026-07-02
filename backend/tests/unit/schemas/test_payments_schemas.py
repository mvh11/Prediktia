"""Pruebas de esquemas de pagos."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.payments import CreateWebpayPaymentRequest, CreateWebpayPaymentResponse


class TestPaymentsSchemas:
    def test_create_request_requires_plan(self):
        with pytest.raises(ValidationError):
            CreateWebpayPaymentRequest()

    def test_create_request_accepts_premium(self):
        req = CreateWebpayPaymentRequest(plan="premium")
        assert req.plan == "premium"

    def test_create_request_rejects_unknown_plan(self):
        with pytest.raises(ValidationError):
            CreateWebpayPaymentRequest(plan="vip")  # type: ignore[arg-type]

    def test_create_response(self):
        resp = CreateWebpayPaymentResponse(url="https://pay.example", token="tok")
        assert resp.token == "tok"
