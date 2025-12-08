"""SePay payment schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal


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
    paid_at: Optional[datetime] = None


class SePayTransaction(BaseModel):
    """SePay transaction from API"""
    id: int
    transaction_date: Optional[str] = None
    amount_in: Optional[float] = None
    amount_out: Optional[float] = None
    accumulated: Optional[float] = None
    transaction_content: Optional[str] = None
    reference_number: Optional[str] = None
    code: Optional[str] = None
    sub_account: Optional[str] = None
    bank_brand_name: Optional[str] = None
    account_number: Optional[str] = None
