"""Credit Service - Manages credit deduction for user actions"""

from uuid import UUID
from sqlmodel import Session, select
from app.models import CreditWallet, CreditActivity, Subscription
import logging

logger = logging.getLogger(__name__)


class CreditService:
    """Service for credit management"""

    def __init__(self, session: Session):
        self.session = session

    def get_user_wallet(self, user_id: UUID) -> CreditWallet | None:
        """Get user's active credit wallet"""
        # First get active subscription
        sub_statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
            .order_by(Subscription.created_at.desc())
        )
        subscription = self.session.exec(sub_statement).first()

        if not subscription:
            return None

        # Get wallet for this subscription
        wallet_statement = (
            select(CreditWallet)
            .where(CreditWallet.user_id == user_id)
            .where(CreditWallet.subscription_id == subscription.id)
            .where(CreditWallet.wallet_type == "subscription")
        )
        return self.session.exec(wallet_statement).first()

    def get_remaining_credits(self, user_id: UUID) -> int:
        """Get remaining credits for user"""
        wallet = self.get_user_wallet(user_id)
        if not wallet:
            return 0
        return (wallet.total_credits or 0) - (wallet.used_credits or 0)

    def deduct_credit(
        self,
        user_id: UUID,
        amount: int = 1,
        reason: str = "chat_message",
        agent_id: UUID | None = None
    ) -> bool:
        """
        Deduct credits from user's wallet.
        
        Args:
            user_id: User ID
            amount: Amount to deduct (default 1)
            reason: Reason for deduction
            agent_id: Optional agent ID if related to agent action
            
        Returns:
            True if deduction successful, False if insufficient credits or no wallet
        """
        wallet = self.get_user_wallet(user_id)
        
        if not wallet:
            logger.warning(f"No wallet found for user {user_id}")
            return False

        remaining = (wallet.total_credits or 0) - (wallet.used_credits or 0)
        
        if remaining < amount:
            logger.warning(f"Insufficient credits for user {user_id}: {remaining} < {amount}")
            return False

        # Deduct credits
        wallet.used_credits = (wallet.used_credits or 0) + amount
        self.session.add(wallet)

        # Log activity
        activity = CreditActivity(
            user_id=user_id,
            agent_id=agent_id,
            wallet_id=wallet.id,
            amount=-amount,
            reason=reason,
            activity_type="deduct"
        )
        self.session.add(activity)

        self.session.commit()
        self.session.refresh(wallet)

        logger.info(f"Deducted {amount} credit(s) from user {user_id}. Remaining: {(wallet.total_credits or 0) - (wallet.used_credits or 0)}")
        return True
