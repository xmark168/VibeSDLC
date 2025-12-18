"""Subscription Service - Manages subscription activation and lifecycle"""

from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
from app.models import (
    Subscription, CreditWallet, Invoice, Order, Plan, User,
    InvoiceStatus
)
import logging

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for subscription management"""

    def __init__(self, session: Session):
        self.session = session

    def get_active_subscription(self, user_id: UUID) -> Subscription | None:
        """Get user's active subscription"""
        statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
            .order_by(Subscription.created_at.desc())
        )
        return self.session.exec(statement).first()

    def activate_subscription(
        self,
        user_id: UUID,
        plan: Plan,
        order: Order,
        auto_renew: bool = True
    ) -> tuple[Subscription, CreditWallet, Invoice]:
        """
        Activate subscription after successful payment
        Returns: (Subscription, CreditWallet, Invoice)
        """
        # Cancel all existing active subscriptions for this user (upgrade/downgrade scenario)
        # and calculate remaining credits to transfer
        existing_subscriptions = self.session.exec(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
        ).all()

        remaining_credits = 0
        for old_sub in existing_subscriptions:
            # Get old wallet and calculate remaining credits
            old_wallet = self.session.exec(
                select(CreditWallet)
                .where(CreditWallet.subscription_id == old_sub.id)
            ).first()
            if old_wallet:
                old_remaining = (old_wallet.total_credits or 0) - (old_wallet.used_credits or 0)
                if old_remaining > 0:
                    remaining_credits += old_remaining
                    logger.info(f"Transferring {old_remaining} remaining credits from subscription {old_sub.id}")

            old_sub.status = "canceled"
            old_sub.auto_renew = False
            self.session.add(old_sub)
            logger.info(f"Canceled existing subscription {old_sub.id} for user {user_id} due to new subscription")

        # Calculate subscription period
        billing_cycle = order.billing_cycle or "monthly"
        start_at = datetime.now(timezone.utc)

        if billing_cycle == "monthly":
            end_at = start_at + timedelta(days=30)
        else:  # yearly
            end_at = start_at + timedelta(days=365)

        # Create Subscription
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status="active",
            start_at=start_at,
            end_at=end_at,
            auto_renew=auto_renew  # Use parameter instead of hardcoded True
        )
        self.session.add(subscription)
        self.session.flush()

        # Create CreditWallet with plan credits + remaining credits from old subscription
        new_total_credits = (plan.monthly_credits or 0) + remaining_credits
        wallet = CreditWallet(
            user_id=user_id,
            wallet_type="subscription",
            subscription_id=subscription.id,
            period_start=start_at,
            period_end=end_at,
            total_credits=new_total_credits,
            used_credits=0
        )
        self.session.add(wallet)
        
        if remaining_credits > 0:
            logger.info(f"Created wallet with {new_total_credits} credits ({plan.monthly_credits} from plan + {remaining_credits} transferred)")

        # Generate Invoice
        invoice = self._generate_invoice(order, subscription)
        self.session.add(invoice)

        # Link order to subscription
        order.subscription_id = subscription.id
        self.session.add(order)

        self.session.commit()
        self.session.refresh(subscription)
        self.session.refresh(wallet)
        self.session.refresh(invoice)

        logger.info(f"Activated subscription {subscription.id} for user {user_id}")
        return subscription, wallet, invoice

    def _generate_invoice(self, order: Order, subscription: Subscription) -> Invoice:
        """Generate invoice for order"""
        # Get user for billing info
        user = self.session.get(User, order.user_id)

        # Generate invoice number (timestamp-based)
        invoice_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{order.id.hex[:8].upper()}"

        invoice = Invoice(
            order_id=order.id,
            invoice_number=invoice_number,
            billing_name=user.full_name or user.email,
            billing_address=user.address or "N/A",
            amount=order.amount,
            currency="VND",
            issue_date=datetime.now(timezone.utc),
            status=InvoiceStatus.PAID
        )
        return invoice

    def add_credits_to_wallet(
        self,
        user_id: UUID,
        credit_amount: int,
        order: Order
    ) -> tuple[CreditWallet, Invoice]:
        """
        Add credits to user's purchased wallet (permanent, no expiry)
        Returns: (CreditWallet, Invoice)
        """
        # Get user's active subscription (needed for invoice generation)
        statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
            .order_by(Subscription.created_at.desc())
        )
        subscription = self.session.exec(statement).first()

        if not subscription:
            raise ValueError("No active subscription found")

        # Get or create purchased wallet (permanent wallet, not tied to subscription lifecycle)
        wallet_statement = (
            select(CreditWallet)
            .where(CreditWallet.user_id == user_id)
            .where(CreditWallet.wallet_type == "purchased")
        )
        wallet = self.session.exec(wallet_statement).first()

        if not wallet:
            # Create new purchased wallet with no expiry
            wallet = CreditWallet(
                user_id=user_id,
                wallet_type="purchased",
                subscription_id=None,
                period_start=datetime.now(timezone.utc),
                period_end=None,
                total_credits=credit_amount,
                used_credits=0
            )
            self.session.add(wallet)
            logger.info(f"Created new purchased wallet for user {user_id} with {credit_amount} credits")
        else:
            # Add credits to existing purchased wallet
            wallet.total_credits = (wallet.total_credits or 0) + credit_amount
            self.session.add(wallet)
            logger.info(f"Added {credit_amount} credits to existing purchased wallet {wallet.id}")

        # Generate invoice
        invoice = self._generate_invoice(order, subscription)
        self.session.add(invoice)

        self.session.commit()
        self.session.refresh(wallet)
        self.session.refresh(invoice)

        logger.info(f"Total purchased credits for user {user_id}: {wallet.total_credits}")
        return wallet, invoice
