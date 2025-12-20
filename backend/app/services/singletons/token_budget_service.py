"""Singleton Token Budget Service for cost control and rate limiting."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID
import logging

from sqlmodel import Session
from app.core.db import engine
from app.models import Project, Agent
from app.models.base import Role

logger = logging.getLogger(__name__)

# Token to credit conversion rate (tokens per credit)
TOKENS_PER_CREDIT = 1000  # 1 credit = 1000 tokens


@dataclass
class TokenBudget:
    """Token budget for a project."""
    project_id: UUID
    daily_limit: int = 10000000  # 10M tokens/day default 
    monthly_limit: int = 20000000  # 20M tokens/month default
    used_today: int = 0
    used_this_month: int = 0
    last_reset_daily: Optional[datetime] = None
    last_reset_monthly: Optional[datetime] = None
    
    @property
    def daily_remaining(self) -> int:
        """Remaining tokens for today."""
        return max(0, self.daily_limit - self.used_today)
    
    @property
    def monthly_remaining(self) -> int:
        """Remaining tokens for this month."""
        return max(0, self.monthly_limit - self.used_this_month)
    
    @property
    def daily_usage_percentage(self) -> float:
        """Daily usage as percentage (0-100)."""
        if self.daily_limit == 0:
            return 100.0
        return (self.used_today / self.daily_limit) * 100
    
    @property
    def monthly_usage_percentage(self) -> float:
        """Monthly usage as percentage (0-100)."""
        if self.monthly_limit == 0:
            return 100.0
        return (self.used_this_month / self.monthly_limit) * 100


class TokenBudgetService:
    """Singleton service for token budget management."""
    
    _instance: Optional['TokenBudgetService'] = None
    _init_lock: asyncio.Lock = asyncio.Lock()
    
    def __init__(self):
        """Private constructor - use get_token_budget_service()."""
        if TokenBudgetService._instance is not None:
            raise RuntimeError(
                "TokenBudgetService is a singleton! "
                "Use get_token_budget_service() instead."
            )
        
        # Shared cache across all requests
        self.cache: Dict[UUID, TokenBudget] = {}
        
        # Per-project locks for thread-safe operations
        self.budget_locks: Dict[UUID, asyncio.Lock] = {}
    
    @classmethod
    async def get_instance(cls) -> 'TokenBudgetService':
        """Get or create singleton instance (thread-safe).
        
        Returns:
            TokenBudgetService singleton instance
        """
        if cls._instance is None:
            async with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _get_session(self) -> Session:
        """Get new database session for each operation."""
        return Session(engine)
    
    def _is_admin(self, session: Session, user_id: UUID) -> bool:
        """Check if user is admin (bypass budget checks)."""
        from app.models import User
        user = session.get(User, user_id)
        return user and user.role == Role.ADMIN

    def _check_user_credits(
        self, 
        session: Session,
        user_id: UUID, 
        estimated_tokens: int
    ) -> Tuple[bool, str]:
        """Check if user has sufficient credits for estimated token usage."""
        try:
            from app.services.credit_service import CreditService
            
            # Calculate estimated credits needed
            estimated_credits = (estimated_tokens + TOKENS_PER_CREDIT - 1) // TOKENS_PER_CREDIT
            
            credit_service = CreditService(session)
            remaining_credits = credit_service.get_remaining_credits(user_id)
            
            logger.debug(
                f"[CREDIT_CHECK] user={user_id}, "
                f"estimated_tokens={estimated_tokens:,}, "
                f"estimated_credits={estimated_credits}, "
                f"remaining_credits={remaining_credits}"
            )
            
            if remaining_credits < estimated_credits:
                logger.warning(
                    f"[CREDIT_CHECK] REJECTED - user={user_id}: "
                    f"insufficient credits ({remaining_credits} < {estimated_credits} required) "
                    f"for {estimated_tokens:,} tokens"
                )
                return False, (
                    f"Insufficient credits. "
                    f"Required: ~{estimated_credits} credits ({estimated_tokens:,} tokens). "
                    f"Available: {remaining_credits} credits. "
                    f"Please purchase more credits to continue."
                )
            
            logger.debug(f"[CREDIT_CHECK] APPROVED - user={user_id}: {remaining_credits} credits available")
            return True, ""
        except Exception as e:
            logger.error(f"[CREDIT_CHECK] ERROR for user {user_id}: {e}", exc_info=True)
            # Fail open to avoid blocking on errors
            return True, ""
        
    async def check_budget(
        self, 
        project_id: UUID, 
        estimated_tokens: int,
        user_id: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Check if project has budget AND user has credits for estimated token usage."""
        session = self._get_session()
        try:
            logger.info(user_id)
            if user_id and self._is_admin(session, user_id):
                logger.debug(f"Admin user {user_id} bypassing budget check")
                return True, ""
            
            # Check user credits first (before project budget)
            if user_id:
                credit_ok, credit_reason = self._check_user_credits(session, user_id, estimated_tokens)
                if not credit_ok:
                    return False, credit_reason
            
            budget = await self._get_budget(session, project_id)
            
            # Reset counters if needed
            self._reset_if_needed(budget)
            
            # Check daily limit
            if budget.used_today + estimated_tokens > budget.daily_limit:
                remaining = budget.daily_remaining
                return False, (
                    f"Daily token limit exceeded. "
                    f"Used: {budget.used_today:,}/{budget.daily_limit:,} tokens "
                    f"({budget.daily_usage_percentage:.1f}%). "
                    f"Remaining: {remaining:,} tokens. "
                    f"Resets at midnight UTC."
                )
            
            # Check monthly limit
            if budget.used_this_month + estimated_tokens > budget.monthly_limit:
                remaining = budget.monthly_remaining
                return False, (
                    f"Monthly token limit exceeded. "
                    f"Used: {budget.used_this_month:,}/{budget.monthly_limit:,} tokens "
                    f"({budget.monthly_usage_percentage:.1f}%). "
                    f"Remaining: {remaining:,} tokens. "
                    f"Resets on 1st of next month."
                )
            
            # Budget available
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking budget for project {project_id}: {e}", exc_info=True)
            # Fail open (allow request) to avoid blocking on errors
            return True, ""
        finally:
            session.close()
    
    async def check_and_reserve(
        self,
        project_id: UUID,
        estimated_tokens: int,
        user_id: Optional[UUID] = None
    ) -> Tuple[bool, str]:
        """Atomic check and reserve tokens (thread-safe)."""
        # Get or create lock for this project
        if project_id not in self.budget_locks:
            self.budget_locks[project_id] = asyncio.Lock()
        
        lock = self.budget_locks[project_id]
        
        async with lock:
            allowed, reason = await self.check_budget(project_id, estimated_tokens, user_id=user_id)
            
            if allowed:
                # Pre-reserve tokens to prevent concurrent over-allocation
                try:
                    # Update cache only (shared across all instances since we're singleton)
                    if project_id in self.cache:
                        budget = self.cache[project_id]
                        budget.used_today += estimated_tokens
                        budget.used_this_month += estimated_tokens
                        logger.debug(
                            f"[BUDGET] Reserved {estimated_tokens:,} tokens for project {project_id}"
                        )
                except Exception as e:
                    logger.error(f"Error reserving tokens: {e}")
            
            return allowed, reason
    
    async def record_usage(
        self, 
        project_id: UUID, 
        tokens_used: int,
        agent_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        deduct_credits: bool = True,
        context: Optional[dict] = None
    ) -> None:
        """Record actual token usage for a project.
        
        Args:
            project_id: Project UUID
            tokens_used: Actual tokens consumed
            agent_id: Optional agent ID for per-agent tracking
            user_id: Optional user ID for credit deduction
            deduct_credits: Whether to deduct credits (default True)
            context: Optional context dict (model_used, task_type, etc.)
        """
        session = self._get_session()
        try:
            budget = await self._get_budget(session, project_id)
            
            # Update project counters
            budget.used_today += tokens_used
            budget.used_this_month += tokens_used
            
            # Persist to database
            await self._save_budget(session, budget)
            
            # Track per-agent usage
            if agent_id:
                await self._record_agent_usage(session, agent_id, tokens_used)
            
            # Deduct credits (skip for admins)
            if deduct_credits and user_id and tokens_used > 0:
                if not self._is_admin(session, user_id):
                    await self._deduct_credits(session, user_id, tokens_used, agent_id, context)
                else:
                    logger.debug(f"Admin user {user_id} - skipping credit deduction")
            
            session.commit()
            
            logger.info(
                f"Recorded {tokens_used:,} tokens for project {project_id}. "
                f"Daily: {budget.used_today:,}/{budget.daily_limit:,} "
                f"({budget.daily_usage_percentage:.1f}%), "
                f"Monthly: {budget.used_this_month:,}/{budget.monthly_limit:,} "
                f"({budget.monthly_usage_percentage:.1f}%)"
            )
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording usage for project {project_id}: {e}", exc_info=True)
        finally:
            session.close()
    
    async def _record_agent_usage(self, session: Session, agent_id: UUID, tokens_used: int) -> None:
        """Record token usage for a specific agent.
        
        Args:
            session: Database session
            agent_id: Agent UUID
            tokens_used: Tokens consumed
        """
        try:
            agent = session.get(Agent, agent_id)
            if agent:
                agent.tokens_used_total = (agent.tokens_used_total or 0) + tokens_used
                agent.tokens_used_today = (agent.tokens_used_today or 0) + tokens_used
                agent.llm_calls_total = (agent.llm_calls_total or 0) + 1
                session.add(agent)
                # Note: Commit is done by caller
                logger.debug(f"Agent {agent_id} token usage: +{tokens_used} (total: {agent.tokens_used_total})")
        except Exception as e:
            logger.error(f"Error recording agent usage: {e}")
    
    async def _deduct_credits(
        self,
        session: Session,
        user_id: UUID, 
        tokens_used: int, 
        agent_id: Optional[UUID] = None,
        context: Optional[dict] = None
    ) -> None:
        """Deduct credits based on token usage with enhanced tracking."""
        try:
            from app.services.credit_service import CreditService
            
            # Calculate credits to deduct (round up)
            credits_to_deduct = (tokens_used + TOKENS_PER_CREDIT - 1) // TOKENS_PER_CREDIT
            
            if credits_to_deduct > 0:
                credit_service = CreditService(session)
                success = credit_service.deduct_credit(
                    user_id=user_id,
                    amount=credits_to_deduct,
                    reason=f"llm_tokens_{tokens_used}",
                    agent_id=agent_id,
                    tokens_used=tokens_used,
                    context=context
                )
                if success:
                    task_info = f", task: {context.get('task_type')}" if context and context.get('task_type') else ""
                    logger.info(f"Deducted {credits_to_deduct} credits for {tokens_used} tokens (user: {user_id}{task_info})")
                else:
                    logger.warning(f"Failed to deduct credits for user {user_id}")
        except Exception as e:
            logger.error(f"Error deducting credits: {e}")
    
    async def get_budget_status(self, project_id: UUID) -> Dict:
        """Get current budget status for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dictionary with budget status
        """
        session = self._get_session()
        try:
            budget = await self._get_budget(session, project_id)
            self._reset_if_needed(budget)
            
            return {
                "project_id": str(project_id),
                "daily": {
                    "limit": budget.daily_limit,
                    "used": budget.used_today,
                    "remaining": budget.daily_remaining,
                    "usage_percentage": round(budget.daily_usage_percentage, 2),
                },
                "monthly": {
                    "limit": budget.monthly_limit,
                    "used": budget.used_this_month,
                    "remaining": budget.monthly_remaining,
                    "usage_percentage": round(budget.monthly_usage_percentage, 2),
                },
                "last_reset_daily": budget.last_reset_daily.isoformat() if budget.last_reset_daily else None,
                "last_reset_monthly": budget.last_reset_monthly.isoformat() if budget.last_reset_monthly else None,
            }
            
        except Exception as e:
            logger.error(f"Error getting budget status for project {project_id}: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            session.close()
    
    async def update_limits(
        self,
        project_id: UUID,
        daily_limit: Optional[int] = None,
        monthly_limit: Optional[int] = None
    ) -> bool:
        """Update budget limits for a project."""
        session = self._get_session()
        try:
            project = session.get(Project, project_id)
            if not project:
                logger.error(f"Project {project_id} not found")
                return False
            
            if daily_limit is not None:
                project.token_budget_daily = daily_limit
            
            if monthly_limit is not None:
                project.token_budget_monthly = monthly_limit
            
            session.add(project)
            session.commit()
            
            # Clear cache to reload new limits
            if project_id in self.cache:
                del self.cache[project_id]
            
            logger.info(
                f"Updated budget limits for project {project_id}: "
                f"daily={daily_limit}, monthly={monthly_limit}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error updating limits for project {project_id}: {e}", exc_info=True)
            session.rollback()
            return False
        finally:
            session.close()
    
    # ===== Internal Methods =====
    
    async def _get_budget(self, session: Session, project_id: UUID) -> TokenBudget:
        """Get budget from cache or load from database.
        
        Args:
            session: Database session
            project_id: Project UUID
            
        Returns:
            TokenBudget instance
        """
        # Check cache first (shared across all requests)
        if project_id in self.cache:
            return self.cache[project_id]
        
        # Load from database
        project = session.get(Project, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        budget = TokenBudget(
            project_id=project_id,
            daily_limit=project.token_budget_daily or 10000000,
            monthly_limit=project.token_budget_monthly or 200000000,
            used_today=project.tokens_used_today or 0,
            used_this_month=project.tokens_used_this_month or 0,
            last_reset_daily=project.budget_last_reset_daily,
            last_reset_monthly=project.budget_last_reset_monthly,
        )
        
        # Cache it (shared cache)
        self.cache[project_id] = budget
        
        return budget
    
    async def _save_budget(self, session: Session, budget: TokenBudget) -> None:
        """Save budget to database.
        
        Args:
            session: Database session
            budget: TokenBudget instance to save
        """
        project = session.get(Project, budget.project_id)
        if not project:
            raise ValueError(f"Project {budget.project_id} not found")
        
        project.tokens_used_today = budget.used_today
        project.tokens_used_this_month = budget.used_this_month
        project.budget_last_reset_daily = budget.last_reset_daily
        project.budget_last_reset_monthly = budget.last_reset_monthly
        
        session.add(project)
        # Note: Commit is done by caller
    
    def _reset_if_needed(self, budget: TokenBudget) -> None:
        """Reset counters if time period has elapsed."""
        now = datetime.now(timezone.utc)
        
        # Reset daily counter
        if budget.last_reset_daily is None:
            # First time - initialize
            budget.used_today = 0
            budget.last_reset_daily = now
            logger.info(f"Initialized daily budget for project {budget.project_id}")
        elif now.date() > budget.last_reset_daily.date():
            # New day - reset
            logger.info(
                f"Daily budget reset for project {budget.project_id}: "
                f"used {budget.used_today:,} tokens yesterday"
            )
            budget.used_today = 0
            budget.last_reset_daily = now
        
        # Reset monthly counter
        if budget.last_reset_monthly is None:
            # First time - initialize
            budget.used_this_month = 0
            budget.last_reset_monthly = now
            logger.info(f"Initialized monthly budget for project {budget.project_id}")
        elif now.month != budget.last_reset_monthly.month or \
             now.year != budget.last_reset_monthly.year:
            # New month - reset
            logger.info(
                f"Monthly budget reset for project {budget.project_id}: "
                f"used {budget.used_this_month:,} tokens last month"
            )
            budget.used_this_month = 0
            budget.last_reset_monthly = now


# Singleton getter
_token_budget_service: Optional[TokenBudgetService] = None


async def get_token_budget_service() -> TokenBudgetService:
    """Get or create singleton token budget service."""
    return await TokenBudgetService.get_instance()
