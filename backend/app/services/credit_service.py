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
        """Get user's active subscription wallet (for backward compatibility)"""
        wallets = self.get_user_wallets(user_id)
        return wallets.get("subscription")

    def get_user_wallets(self, user_id: UUID) -> dict[str, CreditWallet | None]:
        """
        Get all user's wallets (subscription and purchased)
        Returns: {"subscription": CreditWallet | None, "purchased": CreditWallet | None}
        """
        # Get subscription wallet
        sub_statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
            .order_by(Subscription.created_at.desc())
        )
        subscription = self.session.exec(sub_statement).first()

        subscription_wallet = None
        if subscription:
            wallet_statement = (
                select(CreditWallet)
                .where(CreditWallet.user_id == user_id)
                .where(CreditWallet.subscription_id == subscription.id)
                .where(CreditWallet.wallet_type == "subscription")
            )
            subscription_wallet = self.session.exec(wallet_statement).first()

        # Get purchased wallet
        purchased_statement = (
            select(CreditWallet)
            .where(CreditWallet.user_id == user_id)
            .where(CreditWallet.wallet_type == "purchased")
        )
        purchased_wallet = self.session.exec(purchased_statement).first()

        return {
            "subscription": subscription_wallet,
            "purchased": purchased_wallet
        }

    def get_remaining_credits(self, user_id: UUID) -> int:
        """Get total remaining credits from all wallets"""
        wallets = self.get_user_wallets(user_id)
        total = 0
        
        for wallet in wallets.values():
            if wallet:
                remaining = (wallet.total_credits or 0) - (wallet.used_credits or 0)
                total += remaining
        
        return total

    def deduct_credit(
        self,
        user_id: UUID,
        amount: int = 1,
        reason: str = "chat_message",
        agent_id: UUID | None = None,
        tokens_used: int | None = None,
        context: dict | None = None
    ) -> bool:
        """
        Deduct credits from user's wallets with priority:
        1. Subscription wallet first (expires with subscription)
        2. Purchased wallet second (permanent credits)
        
        Args:
            user_id: User ID
            amount: Amount to deduct (default 1)
            reason: Reason for deduction
            agent_id: Optional agent ID if related to agent action
            
        Returns:
            True if deduction successful, False if insufficient credits or no wallet
        """
        wallets = self.get_user_wallets(user_id)
        
        # Check total remaining credits
        total_remaining = 0
        for wallet in wallets.values():
            if wallet:
                remaining = (wallet.total_credits or 0) - (wallet.used_credits or 0)
                total_remaining += remaining
        
        if total_remaining < amount:
            logger.warning(f"Insufficient credits for user {user_id}: {total_remaining} < {amount}")
            return False

        # Deduct from subscription wallet first (use expiring credits first)
        remaining_to_deduct = amount
        subscription_wallet = wallets.get("subscription")
        
        if subscription_wallet and remaining_to_deduct > 0:
            sub_remaining = (subscription_wallet.total_credits or 0) - (subscription_wallet.used_credits or 0)
            if sub_remaining > 0:
                deduct_from_sub = min(sub_remaining, remaining_to_deduct)
                subscription_wallet.used_credits = (subscription_wallet.used_credits or 0) + deduct_from_sub
                self.session.add(subscription_wallet)
                
                # Log activity with enhanced tracking
                activity = CreditActivity(
                    user_id=user_id,
                    agent_id=agent_id,
                    wallet_id=subscription_wallet.id,
                    amount=-deduct_from_sub,
                    reason=reason,
                    activity_type="deduct",
                    tokens_used=tokens_used,
                    model_used=context.get("model_used") if context else None,
                    llm_calls=context.get("llm_calls", 0) if context else 0,
                    project_id=context.get("project_id") if context else None,
                    story_id=context.get("story_id") if context else None,
                    task_type=context.get("task_type") if context else None,
                    execution_id=context.get("execution_id") if context else None,
                )
                self.session.add(activity)
                
                remaining_to_deduct -= deduct_from_sub
                logger.info(f"Deducted {deduct_from_sub} credit(s) from subscription wallet")

        # Deduct remaining from purchased wallet if needed
        purchased_wallet = wallets.get("purchased")
        
        if purchased_wallet and remaining_to_deduct > 0:
            purchased_remaining = (purchased_wallet.total_credits or 0) - (purchased_wallet.used_credits or 0)
            if purchased_remaining > 0:
                deduct_from_purchased = min(purchased_remaining, remaining_to_deduct)
                purchased_wallet.used_credits = (purchased_wallet.used_credits or 0) + deduct_from_purchased
                self.session.add(purchased_wallet)
                
                # Log activity with enhanced tracking
                activity = CreditActivity(
                    user_id=user_id,
                    agent_id=agent_id,
                    wallet_id=purchased_wallet.id,
                    amount=-deduct_from_purchased,
                    reason=reason,
                    activity_type="deduct",
                    tokens_used=tokens_used,
                    model_used=context.get("model_used") if context else None,
                    llm_calls=context.get("llm_calls", 0) if context else 0,
                    project_id=context.get("project_id") if context else None,
                    story_id=context.get("story_id") if context else None,
                    task_type=context.get("task_type") if context else None,
                    execution_id=context.get("execution_id") if context else None,
                )
                self.session.add(activity)
                
                remaining_to_deduct -= deduct_from_purchased
                logger.info(f"Deducted {deduct_from_purchased} credit(s) from purchased wallet")

        self.session.commit()

        # Calculate final remaining
        final_remaining = self.get_remaining_credits(user_id)
        logger.info(f"Deducted total {amount} credit(s) from user {user_id}. Remaining: {final_remaining}")
        return True
