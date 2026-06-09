"""Persistencia de pagos Webpay."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PaymentRow

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_APPROVED = "approved"
PAYMENT_STATUS_REJECTED = "rejected"


def create_pending_payment(
    session: Session,
    *,
    user_id: int,
    plan: str,
    amount: int,
    buy_order: str,
    session_id: str,
) -> PaymentRow:
    row = PaymentRow(
        user_id=user_id,
        plan=plan,
        amount=amount,
        status=PAYMENT_STATUS_PENDING,
        buy_order=buy_order,
        session_id=session_id,
    )
    session.add(row)
    session.flush()
    return row


def get_payment_by_token(session: Session, token: str) -> PaymentRow | None:
    return session.scalar(select(PaymentRow).where(PaymentRow.token == token))


def get_payment_by_buy_order(session: Session, buy_order: str) -> PaymentRow | None:
    return session.scalar(select(PaymentRow).where(PaymentRow.buy_order == buy_order))


def attach_webpay_token(session: Session, payment: PaymentRow, token: str) -> PaymentRow:
    payment.token = token
    session.flush()
    return payment


def set_payment_status(session: Session, payment: PaymentRow, status: str) -> PaymentRow:
    payment.status = status
    session.flush()
    return payment
