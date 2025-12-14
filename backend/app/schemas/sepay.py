"""SePay payment schemas"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SePayCreateRequest(BaseModel):
    """Request to create SePay payment"""
    plan_id: UUID
    billing_cycle: Literal["monthly", "yearly"] = "monthly"
    auto_renew: bool = True


class SePayCreditPurchaseRequest(BaseModel):
    """Request to purchase credits via SePay"""
    credit_amount: int = Field(ge=10, description="Number of credits to purchase")
class SePayQRResponse(BaseModel):
    """Response with SePay QR code info"""
    order_id: UUID
    transaction_code: str
    qr_url: str
    amount: int
    description: str
    expires_at: datetime


class SePayStatusResponse(BaseModel):
    """SePay payment status response"""
    order_id: UUID
    transaction_code: str
    status: str  # pending, paid, expired
    paid_at: datetime | None = None


class SePayTransaction(BaseModel):
    """SePay transaction from API"""
    id: int
    transaction_date: str | None = None
    amount_in: float | None = None
    amount_out: float | None = None
    accumulated: float | None = None
    transaction_content: str | None = None
    reference_number: str | None = None
    code: str | None = None
    sub_account: str | None = None
    bank_brand_name: str | None = None
    account_number: str | None = None
