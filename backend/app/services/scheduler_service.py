"""Periodic task scheduler for system maintenance."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class SchedulerService:
    """Handles periodic system tasks."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Setup scheduled jobs."""
        
        # Daily agent token reset at midnight UTC
        self.scheduler.add_job(
            self._reset_agent_daily_tokens,
            CronTrigger(hour=0, minute=0, timezone="UTC"),
            id="reset_agent_daily_tokens",
            name="Reset agent daily token counters",
            replace_existing=True
        )
        
        # Optional: Cleanup old activities (every Sunday at 2am)
        self.scheduler.add_job(
            self._cleanup_old_activities,
            CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="UTC"),
            id="cleanup_old_activities",
            name="Cleanup activities older than 90 days",
            replace_existing=True
        )
    
    async def _reset_agent_daily_tokens(self):
        """Reset all agents' tokens_used_today to 0."""
        from app.core.db import engine
        from app.models import Agent
        
        try:
            with Session(engine) as session:
                agents = session.exec(select(Agent)).all()
                count = 0
                
                for agent in agents:
                    if agent.tokens_used_today and agent.tokens_used_today > 0:
                        logger.info(
                            f"Resetting {agent.name} daily tokens: "
                            f"{agent.tokens_used_today} → 0"
                        )
                        agent.tokens_used_today = 0
                        session.add(agent)
                        count += 1
                
                session.commit()
                logger.info(f"✓ Reset daily tokens for {count} agents")
                
        except Exception as e:
            logger.error(f"Error resetting agent daily tokens: {e}", exc_info=True)
    
    async def _cleanup_old_activities(self):
        """Delete credit activities older than 90 days."""
        from app.core.db import engine
        from app.models import CreditActivity
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            
            with Session(engine) as session:
                old_activities = session.exec(
                    select(CreditActivity)
                    .where(CreditActivity.created_at < cutoff)
                ).all()
                
                count = len(old_activities)
                for activity in old_activities:
                    session.delete(activity)
                
                session.commit()
                logger.info(f"✓ Cleaned up {count} old activities")
                
        except Exception as e:
            logger.error(f"Error cleaning up activities: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("✓ Scheduler service started")
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        self.scheduler.shutdown()
        logger.info("Scheduler service stopped")
