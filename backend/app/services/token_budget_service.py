"""Token Budget Service for cost control and rate limiting.

This service manages token budgets per project to prevent cost explosions
and ensure fair usage across projects.

Features:
- Daily and monthly token limits per project
- Automatic reset at period boundaries
- Budget checking before task execution
- Usage tracking and analytics
- Graceful rejection when budget exceeded
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from uuid import UUID
import logging

from sqlmodel import Session, select
from app.models import Project
from app.core.db import engine

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Token budget for a project.
    
    Attributes:
        project_id: Project UUID
        daily_limit: Maximum tokens allowed per day
        monthly_limit: Maximum tokens allowed per month
        used_today: Tokens used today (resets daily)
        used_this_month: Tokens used this month (resets monthly)
        last_reset_daily: Last daily reset timestamp
        last_reset_monthly: Last monthly reset timestamp
    """
    project_id: UUID
    daily_limit: int = 100000  # 100K tokens/day default (reasonable for dev)
    monthly_limit: int = 2000000  # 2M tokens/month default
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


class TokenBudgetManager:
    """Manages token budgets and enforces limits.
    
    This manager:
    - Loads budgets from database
    - Checks if requests can proceed based on budget
    - Records token usage
    - Auto-resets counters at period boundaries
    - Caches budgets in memory for performance
    
    Example:
        >>> with Session(engine) as session:
        ...     manager = TokenBudgetManager(session)
        ...     allowed, reason = await manager.check_budget(project_id, 1000)
        ...     if allowed:
        ...         # Process task...
        ...         await manager.record_usage(project_id, actual_tokens)
    """
    
    def __init__(self, session: Session):
        """Initialize budget manager.
        
        Args:
            session: SQLModel session for database operations
        """
        self.session = session
        self.cache: Dict[UUID, TokenBudget] = {}
        
    async def check_budget(
        self, 
        project_id: UUID, 
        estimated_tokens: int
    ) -> Tuple[bool, str]:
        """Check if project has budget for estimated token usage.
        
        Args:
            project_id: Project UUID
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            Tuple of (allowed, reason):
            - (True, "") if request can proceed
            - (False, reason) if request should be rejected
        """
        try:
            budget = await self._get_budget(project_id)
            
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
    
    async def record_usage(self, project_id: UUID, tokens_used: int) -> None:
        """Record actual token usage for a project.
        
        Args:
            project_id: Project UUID
            tokens_used: Actual tokens consumed
        """
        try:
            budget = await self._get_budget(project_id)
            
            # Update counters
            budget.used_today += tokens_used
            budget.used_this_month += tokens_used
            
            # Persist to database
            await self._save_budget(budget)
            
            logger.info(
                f"Recorded {tokens_used:,} tokens for project {project_id}. "
                f"Daily: {budget.used_today:,}/{budget.daily_limit:,} "
                f"({budget.daily_usage_percentage:.1f}%), "
                f"Monthly: {budget.used_this_month:,}/{budget.monthly_limit:,} "
                f"({budget.monthly_usage_percentage:.1f}%)"
            )
            
        except Exception as e:
            logger.error(f"Error recording usage for project {project_id}: {e}", exc_info=True)
    
    async def get_budget_status(self, project_id: UUID) -> Dict:
        """Get current budget status for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dictionary with budget status
        """
        try:
            budget = await self._get_budget(project_id)
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
    
    async def update_limits(
        self,
        project_id: UUID,
        daily_limit: Optional[int] = None,
        monthly_limit: Optional[int] = None
    ) -> bool:
        """Update budget limits for a project.
        
        Args:
            project_id: Project UUID
            daily_limit: New daily limit (None = no change)
            monthly_limit: New monthly limit (None = no change)
            
        Returns:
            True if updated successfully
        """
        try:
            project = self.session.get(Project, project_id)
            if not project:
                logger.error(f"Project {project_id} not found")
                return False
            
            if daily_limit is not None:
                project.token_budget_daily = daily_limit
            
            if monthly_limit is not None:
                project.token_budget_monthly = monthly_limit
            
            self.session.add(project)
            self.session.commit()
            
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
            self.session.rollback()
            return False
    
    # ===== Internal Methods =====
    
    async def _get_budget(self, project_id: UUID) -> TokenBudget:
        """Get budget from cache or load from database.
        
        Args:
            project_id: Project UUID
            
        Returns:
            TokenBudget instance
        """
        # Check cache first
        if project_id in self.cache:
            return self.cache[project_id]
        
        # Load from database
        project = self.session.get(Project, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        budget = TokenBudget(
            project_id=project_id,
            daily_limit=project.token_budget_daily or 100000,
            monthly_limit=project.token_budget_monthly or 2000000,
            used_today=project.tokens_used_today or 0,
            used_this_month=project.tokens_used_this_month or 0,
            last_reset_daily=project.budget_last_reset_daily,
            last_reset_monthly=project.budget_last_reset_monthly,
        )
        
        # Cache it
        self.cache[project_id] = budget
        
        return budget
    
    async def _save_budget(self, budget: TokenBudget) -> None:
        """Save budget to database.
        
        Args:
            budget: TokenBudget instance to save
        """
        project = self.session.get(Project, budget.project_id)
        if not project:
            raise ValueError(f"Project {budget.project_id} not found")
        
        project.tokens_used_today = budget.used_today
        project.tokens_used_this_month = budget.used_this_month
        project.budget_last_reset_daily = budget.last_reset_daily
        project.budget_last_reset_monthly = budget.last_reset_monthly
        
        self.session.add(project)
        self.session.commit()
    
    def _reset_if_needed(self, budget: TokenBudget) -> None:
        """Reset counters if time period has elapsed.
        
        Args:
            budget: TokenBudget instance to check and reset
        """
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
