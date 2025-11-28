"""Subscription and Credit Wallet Schemas"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from app.schemas.plan import PlanPublic


class SubscriptionPublic(BaseModel):
    """Public subscription data"""
    id: UUID
    status: str  # 'active', 'expired', 'canceled', 'pending'
    start_at: datetime | None = None
    end_at: datetime | None = None
    auto_renew: bool = True
    plan: PlanPublic


class CreditWalletPublic(BaseModel):
    """Public credit wallet data"""
    id: UUID
    total_credits: int
    used_credits: int
    remaining_credits: int
    period_start: datetime | None = None
    period_end: datetime | None = None


class UserSubscriptionResponse(BaseModel):
    """User subscription with credit wallet"""
    subscription: SubscriptionPublic | None = None
    credit_wallet: CreditWalletPublic | None = None


class UpdateAutoRenew(BaseModel):
    """Update auto-renew setting"""
    auto_renew: bool
