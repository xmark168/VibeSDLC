"""Pool Service"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AgentPool, AgentPoolMetrics, PoolType


class PoolService:
    """Service for managing agent pool"""
    
    def __init__(self, session: Session):
        self.session = session
    
    # ===== Pool CRUD =====
    
    def create_pool(
        self,
        pool_name: str,
        role_type: Optional[str] = None,
        pool_type: PoolType = PoolType.FREE,
        max_agents: int = 100,
        health_check_interval: int = 60,
        llm_model_config: Optional[dict] = None,
        allowed_template_ids: Optional[list[str]] = None,
        created_by: Optional[UUID] = None,
        auto_created: bool = False,
    ) -> AgentPool:
        """Create a new agent pool in database."""
        pool = AgentPool(
            pool_name=pool_name,
            role_type=role_type,
            pool_type=pool_type,
            max_agents=max_agents,
            health_check_interval=health_check_interval,
            llm_model_config=llm_model_config,
            allowed_template_ids=allowed_template_ids,
            created_by=created_by,
            auto_created=auto_created,
            is_active=True,
        )
        self.session.add(pool)
        self.session.commit()
        self.session.refresh(pool)
        return pool
    
    def get_pool_by_name(self, pool_name: str) -> Optional[AgentPool]:
        """Get pool by name."""
        statement = select(AgentPool).where(AgentPool.pool_name == pool_name)
        return self.session.exec(statement).first()
    
    def get_pool_by_id(self, pool_id: UUID) -> Optional[AgentPool]:
        """Get pool by ID."""
        return self.session.get(AgentPool, pool_id)
    
    def get_active_pools(self, role_type: Optional[str] = None) -> list[AgentPool]:
        """Get all active pools, optionally filtered by role_type."""
        statement = select(AgentPool).where(AgentPool.is_active == True)
        if role_type:
            statement = statement.where(AgentPool.role_type == role_type)
        return list(self.session.exec(statement).all())
    
    def get_all_pools(self) -> list[AgentPool]:
        """Get all pools."""
        statement = select(AgentPool)
        return list(self.session.exec(statement).all())
    
    def update_pool(
        self,
        pool_id: UUID,
        updated_by: Optional[UUID] = None,
        **updates
    ) -> Optional[AgentPool]:
        """Update pool fields."""
        pool = self.session.get(AgentPool, pool_id)
        if not pool:
            return None
        
        for key, value in updates.items():
            if hasattr(pool, key):
                setattr(pool, key, value)
        
        if updated_by:
            pool.updated_by = updated_by
        
        self.session.add(pool)
        self.session.commit()
        self.session.refresh(pool)
        return pool
    
    def delete_pool(self, pool_id: UUID) -> bool:
        """Delete a pool."""
        pool = self.session.get(AgentPool, pool_id)
        if not pool:
            return False
        
        self.session.delete(pool)
        self.session.commit()
        return True
    
    # ===== Pool Status Management =====
    
    def mark_pool_started(self, pool_id: UUID) -> Optional[AgentPool]:
        """Mark pool as started."""
        return self.update_pool(
            pool_id,
            is_active=True,
            last_started_at=datetime.now(timezone.utc)
        )
    
    def mark_pool_stopped(self, pool_id: UUID) -> Optional[AgentPool]:
        """Mark pool as stopped."""
        return self.update_pool(
            pool_id,
            is_active=False,
            last_stopped_at=datetime.now(timezone.utc)
        )
    
    def increment_spawn_count(self, pool_id: UUID) -> Optional[AgentPool]:
        """Increment total_spawned and current_agent_count."""
        pool = self.session.get(AgentPool, pool_id)
        if not pool:
            return None
        
        pool.total_spawned += 1
        pool.current_agent_count += 1
        self.session.add(pool)
        self.session.commit()
        self.session.refresh(pool)
        return pool
    
    def increment_terminate_count(self, pool_id: UUID) -> Optional[AgentPool]:
        """Increment total_terminated and decrement current_agent_count."""
        pool = self.session.get(AgentPool, pool_id)
        if not pool:
            return None
        
        pool.total_terminated += 1
        pool.current_agent_count = max(0, pool.current_agent_count - 1)
        self.session.add(pool)
        self.session.commit()
        self.session.refresh(pool)
        return pool
    
    def update_agent_count(self, pool_id: UUID, count: int) -> Optional[AgentPool]:
        """Set current agent count directly."""
        return self.update_pool(pool_id, current_agent_count=count)
    
    # ===== Metrics Management =====
    
    def create_metrics_snapshot(
        self,
        pool_id: UUID,
        period_start: datetime,
        period_end: datetime,
        total_tokens_used: int = 0,
        tokens_per_model: Optional[dict] = None,
        total_requests: int = 0,
        requests_per_model: Optional[dict] = None,
        peak_agent_count: int = 0,
        avg_agent_count: float = 0.0,
        total_executions: int = 0,
        successful_executions: int = 0,
        failed_executions: int = 0,
        avg_execution_duration_ms: Optional[float] = None,
        snapshot_metadata: Optional[dict] = None,
    ) -> AgentPoolMetrics:
        """Create a metrics snapshot for a pool."""
        metrics = AgentPoolMetrics(
            pool_id=pool_id,
            period_start=period_start,
            period_end=period_end,
            total_tokens_used=total_tokens_used,
            tokens_per_model=tokens_per_model or {},
            total_requests=total_requests,
            requests_per_model=requests_per_model or {},
            peak_agent_count=peak_agent_count,
            avg_agent_count=avg_agent_count,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            avg_execution_duration_ms=avg_execution_duration_ms,
            snapshot_metadata=snapshot_metadata,
        )
        self.session.add(metrics)
        self.session.commit()
        self.session.refresh(metrics)
        return metrics
    
    def get_pool_metrics(
        self,
        pool_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list[AgentPoolMetrics]:
        """Get metrics for a pool within date range."""
        statement = select(AgentPoolMetrics).where(AgentPoolMetrics.pool_id == pool_id)
        
        if start_date:
            statement = statement.where(AgentPoolMetrics.period_start >= start_date)
        if end_date:
            statement = statement.where(AgentPoolMetrics.period_end <= end_date)
        
        statement = statement.order_by(AgentPoolMetrics.period_start.desc()).limit(limit)
        return list(self.session.exec(statement).all())
    
    def cleanup_old_metrics(self, days: int = 90) -> int:
        """Delete metrics older than specified days."""
        cutoff_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timezone.timedelta(days=days)
        
        statement = select(AgentPoolMetrics).where(
            AgentPoolMetrics.period_end < cutoff_date
        )
        metrics_to_delete = self.session.exec(statement).all()
        
        count = 0
        for metric in metrics_to_delete:
            self.session.delete(metric)
            count += 1
        
        if count > 0:
            self.session.commit()
        
        return count


class AsyncPoolService:
    """Async pool service for high-performance operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, pool_id: UUID) -> Optional[AgentPool]:
        """Get pool by ID (async)."""
        result = await self.session.execute(
            select(AgentPool).where(AgentPool.id == pool_id)
        )
        return result.scalar_one_or_none()
    
    async def create_pool(self, pool_data: dict) -> AgentPool:
        """Create new pool (async)."""
        pool = AgentPool(**pool_data)
        self.session.add(pool)
        await self.session.flush()
        await self.session.refresh(pool)
        return pool
    
    async def get_available_pools(self, project_id: UUID) -> List[AgentPool]:
        """Get available pools for a project (async)."""
        result = await self.session.execute(
            select(AgentPool)
            .where(AgentPool.project_id == project_id)
            .where(AgentPool.is_active == True)
        )
        return list(result.scalars().all())
