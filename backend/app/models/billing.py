"""Billing, subscription, and payment models."""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, BigInteger, Text
from sqlmodel import Field, Relationship, Column

from app.models.base import BaseModel, OrderType, OrderStatus, InvoiceStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.agent import Agent


class Plan(BaseModel, table=True):
    __tablename__ = "plans"

    code: str | None = Field(default=None, sa_column=Column(Text))
    name: str | None = Field(default=None, sa_column=Column(Text))
    description: str | None = Field(default=None, sa_column=Column(Text))

    monthly_price: int | None = Field(default=None)
    yearly_discount_percentage: float | None = Field(default=None)
    currency: str | None = Field(default=None, sa_column=Column(Text))
    monthly_credits: int | None = Field(default=None)
    additional_credit_price: int | None = Field(default=None)
    available_project: int | None = Field(default=None)
    is_active: bool = Field(default=True, nullable=True)

    tier: str | None = Field(default="pay", sa_column=Column(Text))
    sort_index: int | None = Field(default=0)
    is_featured: bool = Field(default=False)
    is_custom_price: bool = Field(default=False)
    features_text: str | None = Field(default=None, sa_column=Column(Text))

    plan_subscriptions: list["Subscription"] = Relationship(
        back_populates="plan", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @property
    def yearly_price(self) -> int | None:
        if self.monthly_price is not None and self.yearly_discount_percentage is not None:
            annual_monthly_cost = self.monthly_price * 12
            yearly_price = annual_monthly_cost * (1 - self.yearly_discount_percentage / 100)
            return round(yearly_price)
        return None


class Subscription(BaseModel, table=True):
    __tablename__ = "subscriptions"

    user_id: UUID | None = Field(foreign_key="users.id", nullable=True, ondelete="CASCADE")
    plan_id: UUID = Field(foreign_key="plans.id", nullable=True, ondelete="CASCADE")

    status: str | None = Field(default=None, sa_column=Column(Text))
    start_at: datetime | None = Field(default=None)
    end_at: datetime | None = Field(default=None)
    auto_renew: bool = Field(default=True, nullable=True)

    user: "User" = Relationship(back_populates="user_subscriptions")
    plan: Plan = Relationship(back_populates="plan_subscriptions")

    subscription_wallets: list["CreditWallet"] = Relationship(
        back_populates="subscription", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class CreditWallet(BaseModel, table=True):
    __tablename__ = "credit_wallets"

    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    wallet_type: str | None = Field(default=None, sa_column=Column(Text))

    subscription_id: UUID | None = Field(default=None, foreign_key="subscriptions.id", ondelete="SET NULL")
    period_start: datetime | None = Field(default=None)
    period_end: datetime | None = Field(default=None)

    total_credits: int | None = Field(default=None)
    used_credits: int | None = Field(default=None)

    user: Optional["User"] = Relationship()
    subscription: Optional["Subscription"] = Relationship(back_populates="subscription_wallets")
    credit_activities: list["CreditActivity"] = Relationship(
        back_populates="wallet", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class CreditActivity(BaseModel, table=True):
    __tablename__ = "credit_activities"

    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="CASCADE")
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", ondelete="CASCADE")
    wallet_id: UUID | None = Field(default=None, foreign_key="credit_wallets.id", ondelete="CASCADE")

    # Credit and reason
    amount: int | None = Field(default=None)
    reason: str | None = Field(default=None, sa_column=Column(Text))
    activity_type: str | None = Field(default=None, sa_column=Column(Text))
    
    # Token tracking details
    tokens_used: int | None = Field(default=None)
    model_used: str | None = Field(default=None, sa_column=Column(Text))
    llm_calls: int | None = Field(default=0)
    
    # Context for better monitoring
    project_id: UUID | None = Field(default=None, foreign_key="projects.id", ondelete="CASCADE")
    story_id: UUID | None = Field(default=None, foreign_key="stories.id", ondelete="SET NULL")
    task_type: str | None = Field(default=None, sa_column=Column(Text))
    execution_id: UUID | None = Field(default=None, foreign_key="agent_executions.id", ondelete="SET NULL")

    # Relationships
    user: Optional["User"] = Relationship()
    agent: Optional["Agent"] = Relationship()
    wallet: Optional[CreditWallet] = Relationship(back_populates="credit_activities")
    project: Optional["Project"] = Relationship()
    story: Optional["Story"] = Relationship()


class Order(BaseModel, table=True):
    __tablename__ = "orders"

    user_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    order_type: OrderType = Field(nullable=False)
    subscription_id: UUID | None = Field(default=None, foreign_key="subscriptions.id", ondelete="SET NULL")

    amount: float = Field(nullable=False)
    status: OrderStatus = Field(default=OrderStatus.PENDING, nullable=False)
    paid_at: datetime | None = Field(default=None)
    is_active: bool = Field(default=True, nullable=False)

    payos_order_code: int | None = Field(default=None, sa_column=Column(BigInteger, unique=True, index=True))
    payos_transaction_id: str | None = Field(default=None, sa_column=Column(Text))
    payment_link_id: str | None = Field(default=None, sa_column=Column(Text))
    qr_code: str | None = Field(default=None, sa_column=Column(Text))
    checkout_url: str | None = Field(default=None, sa_column=Column(Text))
    
    # SePay fields
    sepay_transaction_code: str | None = Field(default=None, sa_column=Column(Text, unique=True, index=True))
    sepay_transaction_id: str | None = Field(default=None, sa_column=Column(Text))

    billing_cycle: str | None = Field(default="monthly", sa_column=Column(Text))
    plan_code: str | None = Field(default=None, sa_column=Column(Text))
    auto_renew: bool = Field(default=True, nullable=False)
    credit_amount: int | None = Field(default=None, nullable=True)

    user: "User" = Relationship()
    subscription: Optional["Subscription"] = Relationship()
    invoices: list["Invoice"] = Relationship(
        back_populates="order", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Invoice(BaseModel, table=True):
    __tablename__ = "invoices"

    order_id: UUID = Field(foreign_key="orders.id", nullable=False, ondelete="CASCADE")
    invoice_number: str = Field(unique=True, index=True, nullable=False)

    billing_name: str = Field(nullable=False)
    billing_address: str | None = Field(default=None, sa_column=Column(Text))

    amount: float = Field(nullable=False)
    currency: str = Field(default="VND", nullable=False)

    issue_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False  # Strip timezone for asyncpg
    )
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT, nullable=False)

    order: Order = Relationship(back_populates="invoices")
