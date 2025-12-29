"""Credit Service - Manages credit deduction for user actions"""

from uuid import UUID
from sqlmodel import Session, select, text
from app.models import CreditWallet, CreditActivity, Subscription
from datetime import datetime, timezone
import logging
import asyncio

logger = logging.getLogger(__name__)


class CreditService:
    """Service for credit management with atomic operations"""

    def __init__(self, session: Session):
        self.session = session
    
    def _schedule_credit_broadcast(
        self,
        user_id: UUID,
        amount_changed: int,
        remaining_credits: int,
        total_credits: int,
        reason: str,
        context: dict | None = None,
    ):
        """Schedule async WebSocket broadcast from sync context."""
        try:
            async def broadcast():
                from app.websocket.connection_manager import connection_manager
                
                message = {
                    "type": "credit_update",
                    "data": {
                        "amount_changed": amount_changed,
                        "remaining_credits": remaining_credits,
                        "total_credits": total_credits,
                        "reason": reason,
                        "agent_name": context.get("agent_name") if context else None,
                        "tokens_used": context.get("tokens_used") if context else None,
                        "model_used": context.get("model_used") if context else None,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                }
                
                # Broadcast to user's project
                if context and context.get("project_id"):
                    try:
                        project_id = UUID(context["project_id"]) if isinstance(context["project_id"], str) else context["project_id"]
                        await connection_manager.broadcast_to_project(message, project_id)
                        logger.debug(f"Broadcasted credit update to project {project_id}")
                    except Exception as e:
                        logger.debug(f"Failed to broadcast credit update: {e}")
            
            # Try to get running loop, create task if available
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(broadcast())
            except RuntimeError:
                # No running loop, skip broadcast
                logger.debug("No event loop for credit broadcast")
        except Exception as e:
            logger.warning(f"Error scheduling credit broadcast: {e}")

    def _acquire_user_lock(self, user_id: UUID) -> None:
        """Acquire advisory lock for user to prevent race conditions.
        
        Uses PostgreSQL advisory lock with user_id hash for atomic credit operations.
        """
        try:
            # Use first 8 bytes of UUID as lock key (PostgreSQL advisory lock uses bigint)
            lock_key = int(user_id.int & 0x7FFFFFFFFFFFFFFF)  # Ensure positive bigint
            self.session.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))
        except Exception as e:
            logger.warning(f"Failed to acquire advisory lock for user {user_id}: {e}")

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

    def has_sufficient_credits(self, user_id: UUID, amount: int = 1) -> bool:
        """Check if user has sufficient credits without deducting.
        
        Args:
            user_id: User ID
            amount: Amount to check
            
        Returns:
            True if user has enough credits
        """
        return self.get_remaining_credits(user_id) >= amount

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
        Atomically deduct credits from user's wallets with priority:
        1. Subscription wallet first (expires with subscription)
        2. Purchased wallet second (permanent credits)
        
        Uses PostgreSQL advisory lock to prevent race conditions.
        
        Args:
            user_id: User ID
            amount: Amount to deduct (default 1)
            reason: Reason for deduction
            agent_id: Optional agent ID if related to agent action
            
        Returns:
            True if deduction successful, False if insufficient credits or no wallet
        """
        # Acquire lock to prevent race conditions
        self._acquire_user_lock(user_id)
        
        wallets = self.get_user_wallets(user_id)
        
        # Check total remaining credits
        total_remaining = 0
        for wallet in wallets.values():
            if wallet:
                remaining = (wallet.total_credits or 0) - (wallet.used_credits or 0)
                total_remaining += remaining
        
        if total_remaining < amount:
            logger.warning(
                f"[CREDIT_DEDUCT] REJECTED - user={user_id}: "
                f"insufficient credits ({total_remaining} < {amount} required), "
                f"reason={reason}"
            )
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
                logger.info(
                    f"[CREDIT_DEDUCT] user={user_id}: "
                    f"-{deduct_from_sub} from subscription wallet, "
                    f"reason={reason}"
                )

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
                logger.info(
                    f"[CREDIT_DEDUCT] user={user_id}: "
                    f"-{deduct_from_purchased} from purchased wallet, "
                    f"reason={reason}"
                )

        self.session.commit()

        # Calculate final remaining
        final_remaining = self.get_remaining_credits(user_id)
        logger.info(
            f"[CREDIT_DEDUCT] SUCCESS - user={user_id}: "
            f"total_deducted={amount}, remaining={final_remaining}, "
            f"reason={reason}, tokens={tokens_used or 'N/A'}"
        )
        
        # Broadcast credit update via WebSocket
        wallets = self.get_user_wallets(user_id)
        total_credits = 0
        for wallet in wallets.values():
            if wallet:
                total_credits += wallet.total_credits or 0
        
        # Add tokens_used to context if provided
        broadcast_context = context.copy() if context else {}
        if tokens_used is not None:
            broadcast_context["tokens_used"] = tokens_used
        
        self._schedule_credit_broadcast(
            user_id=user_id,
            amount_changed=-amount,
            remaining_credits=final_remaining,
            total_credits=total_credits,
            reason=reason,
            context=broadcast_context,
        )
        
        return True
