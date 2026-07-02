"""Pruebas del repositorio de pagos (SQLAlchemy mockeado)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.db.models import PaymentRow
from app.services.payments import (
    PAYMENT_STATUS_APPROVED,
    PAYMENT_STATUS_PENDING,
    attach_webpay_token,
    create_pending_payment,
    get_payment_by_buy_order,
    get_payment_by_token,
    set_payment_status,
)


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    return session


class TestPaymentsRepository:
    def test_create_pending_payment(self, mock_session):
        payment = create_pending_payment(
            mock_session,
            user_id=1,
            plan="premium",
            amount=4990,
            buy_order="P1001",
            session_id="s-abc",
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        assert payment.user_id == 1
        assert payment.status == PAYMENT_STATUS_PENDING
        assert payment.amount == 4990

    def test_get_payment_by_token(self, mock_session):
        expected = PaymentRow(user_id=1, plan="premium", amount=4990, buy_order="B1", session_id="S1")
        mock_session.scalar.return_value = expected
        result = get_payment_by_token(mock_session, "token-123")
        assert result is expected
        mock_session.scalar.assert_called_once()

    def test_get_payment_by_buy_order(self, mock_session):
        mock_session.scalar.return_value = None
        assert get_payment_by_buy_order(mock_session, "missing") is None

    def test_attach_webpay_token(self, mock_session):
        payment = PaymentRow(user_id=1, plan="premium", amount=4990, buy_order="B2", session_id="S2")
        updated = attach_webpay_token(mock_session, payment, "tok-xyz")
        assert updated.token == "tok-xyz"
        mock_session.flush.assert_called_once()

    def test_set_payment_status(self, mock_session):
        payment = PaymentRow(user_id=1, plan="premium", amount=4990, buy_order="B3", session_id="S3")
        set_payment_status(mock_session, payment, PAYMENT_STATUS_APPROVED)
        assert payment.status == PAYMENT_STATUS_APPROVED
