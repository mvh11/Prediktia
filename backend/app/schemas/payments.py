"""Esquemas de pagos Webpay Plus."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PaymentStatus = Literal["pending", "approved", "rejected"]
PaymentPlan = Literal["premium"]


class CreateWebpayPaymentRequest(BaseModel):
    plan: PaymentPlan = Field(description="Plan a contratar (inicial: premium).")


class CreateWebpayPaymentResponse(BaseModel):
    url: str
    token: str
