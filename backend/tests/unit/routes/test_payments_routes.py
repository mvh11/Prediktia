"""Pruebas de rutas de pagos Webpay."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_user
from app.config import get_settings
from app.db.models import PaymentRow
from tests.fixtures.settings import make_test_settings


@contextmanager
def _payments_session(session: MagicMock):
    @contextmanager
    def fake_scope(_url: str):
        yield session

    with patch("app.api.routes.payments.session_scope", fake_scope):
        yield


class TestPaymentsRoutes:
    def test_create_requires_auth(self, client: TestClient):
        res = client.post("/payments/webpay/create", json={"plan": "premium"})
        assert res.status_code == 401

    def test_create_webpay_not_configured(self, client: TestClient, free_user):
        no_webpay = make_test_settings().model_copy(
            update={"webpay_commerce_code": "", "app_env": "development"}
        )
        client.app.dependency_overrides[get_settings] = lambda: no_webpay
        client.app.dependency_overrides[get_current_user] = lambda: free_user
        try:
            res = client.post("/payments/webpay/create", json={"plan": "premium"})
        finally:
            client.app.dependency_overrides.pop(get_current_user, None)
        assert res.status_code == 503

    def test_create_premium_already_active(self, client: TestClient, premium_user):
        client.app.dependency_overrides[get_current_user] = lambda: premium_user
        try:
            res = client.post("/payments/webpay/create", json={"plan": "premium"})
        finally:
            client.app.dependency_overrides.pop(get_current_user, None)
        assert res.status_code == 400

    def test_create_success(self, client: TestClient, free_user):
        session = MagicMock()
        payment = PaymentRow(
            id=1,
            user_id=free_user.id,
            plan="premium",
            amount=4990,
            buy_order="P1",
            session_id="s1",
        )
        client.app.dependency_overrides[get_current_user] = lambda: free_user
        try:
            with _payments_session(session), patch(
                "app.api.routes.payments.create_pending_payment",
                return_value=payment,
            ), patch(
                "app.api.routes.payments.create_webpay_transaction",
                return_value={"url": "https://pay.example", "token": "tok123"},
            ), patch(
                "app.api.routes.payments.attach_webpay_token",
                return_value=payment,
            ):
                res = client.post("/payments/webpay/create", json={"plan": "premium"})
        finally:
            client.app.dependency_overrides.pop(get_current_user, None)
        assert res.status_code == 200
        body = res.json()
        assert body["url"] == "https://pay.example"
        assert body["token"] == "tok123"

    def test_return_without_token_redirects_failed(self, client: TestClient):
        res = client.get("/payments/webpay/return", follow_redirects=False)
        assert res.status_code == 303
        assert "payment=failed" in res.headers["location"]

    def test_return_approved_redirects_success(self, client: TestClient):
        session = MagicMock()
        payment = PaymentRow(
            id=2,
            user_id=3,
            plan="premium",
            amount=4990,
            buy_order="P2",
            session_id="s2",
            token="tok-abc",
        )
        with _payments_session(session), patch(
            "app.api.routes.payments.commit_webpay_transaction",
            return_value={"response_code": 0, "buy_order": "P2"},
        ), patch(
            "app.api.routes.payments.get_payment_by_token",
            return_value=payment,
        ), patch("app.api.routes.payments.set_payment_status"), patch(
            "app.api.routes.payments.update_user_tier"
        ):
            res = client.get(
                "/payments/webpay/return",
                params={"token_ws": "tok-abc"},
                follow_redirects=False,
            )
        assert res.status_code == 303
        assert "payment=success" in res.headers["location"]

    def test_payment_history(self, client: TestClient, free_user):
        session = MagicMock()
        row = PaymentRow(
            id=9,
            user_id=free_user.id,
            plan="premium",
            amount=4990,
            status="approved",
            buy_order="B9",
            session_id="S9",
            created_at=datetime.now(timezone.utc),
        )
        client.app.dependency_overrides[get_current_user] = lambda: free_user
        try:
            with _payments_session(session), patch(
                "app.api.routes.payments.list_user_payments",
                return_value=[row],
            ):
                res = client.get("/payments/history")
        finally:
            client.app.dependency_overrides.pop(get_current_user, None)
        assert res.status_code == 200
        assert len(res.json()["items"]) == 1
