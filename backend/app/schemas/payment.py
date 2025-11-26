"""Payment schemas for PayOS integration"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal


class PaymentItemData(BaseModel):
    """PayOS Item data schema"""
    name: str
    quantity: int = 1
    price: int  # In VND


class CreatePaymentRequest(BaseModel):
    """Request to create payment order"""
    plan_id: UUID
    billing_cycle: Literal["monthly", "yearly"] = "monthly"
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PaymentLinkResponse(BaseModel):
    """Response containing payment link details"""
    order_id: UUID
    payos_order_code: int
    checkout_url: str
    qr_code: str
    amount: int
    description: str


class PaymentStatusResponse(BaseModel):
    """Payment status check response"""
    order_id: UUID
    status: str  # pending, paid, failed, canceled
    paid_at: Optional[datetime] = None
    payos_transaction_id: Optional[str] = None


class PayOSWebhookData(BaseModel):
    """PayOS webhook payload"""
    orderCode: int
    amount: int
    description: str
    accountNumber: str
    reference: str
    transactionDateTime: str
    currency: str = "VND"
    paymentLinkId: str
    code: str
    desc: str
    counterAccountBankId: Optional[str] = None
    counterAccountBankName: Optional[str] = None
    counterAccountName: Optional[str] = None
    counterAccountNumber: Optional[str] = None
    virtualAccountName: Optional[str] = None
    virtualAccountNumber: Optional[str] = None


class WebhookRequest(BaseModel):
    """Webhook request with signature"""
    data: PayOSWebhookData
    signature: str
