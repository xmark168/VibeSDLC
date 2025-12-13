"""Warm Pool Manager - Pre-spawn agents for reduced latency.

Maintains a minimum number of idle agents per role type, ready to accept tasks
immediately without spawn overhead.

Features:
- Configurable minimum agents per role
- Background maintenance loop
- Project-agnostic warm agents (assigned on first task)
- Integration with pool managers
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

from app.models import AgentStatus

if TYPE_CHECKING:
    from app.agents.core.agent_pool_manager import AgentPoolManager

logger = logging.getLogger(__name__)


class WarmPoolManager:
    """Maintain minimum warm (idle) agents per role type.
    
    Periodically checks agent counts and spawns new agents if below threshold.
    Warm agents are created without project assignment and assigned on first task.
    """
    
    def __init__(
        self,
        manager_registry: Dict[str, "AgentPoolManager"],
        min_agents_config: Dict[str, int],
        check_interval: int = 30,
        enabled: bool = True,
    ):
        """Initialize warm pool manager.
        
        Args:
            manager_registry: Dict of pool_name -> AgentPoolManager
            min_agents_config: Dict of role_type -> minimum idle count
            check_interval: Seconds between maintenance checks
            enabled: Whether warm pool is enabled
        """
        self.registry = manager_registry
        self.min_agents = min_agents_config
        self.check_interval = check_interval
        self.enabled = enabled
        
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_check: Optional[datetime] = None
        
        # Statistics
        self._total_spawned = 0
        self._spawn_failures = 0
        
        logger.info(
            f"WarmPoolManager initialized "
            f"(enabled={enabled}, interval={check_interval}s, "
            f"config={min_agents_config})"
        )
    
    async def start(self) -> bool:
        """Start the warm pool maintenance loop.
        
        Returns:
            True if started successfully
        """
        if not self.enabled:
            logger.info("WarmPoolManager disabled, not starting")
            return False
        
        if self._running:
            logger.warning("WarmPoolManager already running")
            return False
        
        try:
            self._running = True
            self._task = asyncio.create_task(self._maintenance_loop())
            logger.info("WarmPoolManager started")
            
            # Do initial check immediately
            await self._ensure_warm_agents()
            
            return True
        except Exception as e:
            logger.error(f"Failed to start WarmPoolManager: {e}", exc_info=True)
            self._running = False
            return False
    
    async def stop(self) -> bool:
        """Stop the warm pool maintenance loop.
        
        Returns:
            True if stopped successfully
        """
        if not self._running:
            return True
        
        try:
            self._running = False
            
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            
            logger.info("WarmPoolManager stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping WarmPoolManager: {e}", exc_info=True)
            return False
    
    async def _maintenance_loop(self) -> None:
        """Background maintenance loop."""
        logger.info("WarmPoolManager maintenance loop started")
        
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                await self._ensure_warm_agents()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in warm pool maintenance: {e}", exc_info=True)
        
        logger.info("WarmPoolManager maintenance loop stopped")
    
    async def _ensure_warm_agents(self) -> None:
        """Ensure minimum warm agents exist for each role."""
        self._last_check = datetime.now(timezone.utc)
        
        for role, min_count in self.min_agents.items():
            try:
                await self._ensure_role_warm_agents(role, min_count)
            except Exception as e:
                logger.error(f"Error ensuring warm agents for {role}: {e}", exc_info=True)
    
    async def _ensure_role_warm_agents(self, role: str, min_count: int) -> None:
        """Ensure minimum warm agents for a specific role.
        
        Args:
            role: Role type (e.g., "developer")
            min_count: Minimum idle agents required
        """
        pool_name = f"{role}_pool"
        pool = self.registry.get(pool_name)
        
        if not pool:
            # Try universal pool
            pool = self.registry.get("universal_pool")
            if not pool:
                logger.debug(f"No pool found for role {role}")
                return
        
        # Count current idle agents of this role
        idle_count = self._count_idle_agents(pool, role)
        
        if idle_count >= min_count:
            logger.debug(f"[WARM_POOL] {role}: {idle_count}/{min_count} idle agents (OK)")
            return
        
        # Need to spawn more
        needed = min_count - idle_count
        logger.info(
            f"[WARM_POOL] {role}: {idle_count}/{min_count} idle agents, "
            f"spawning {needed} warm agents"
        )
        
        for i in range(needed):
            success = await self._spawn_warm_agent(pool, role)
            if not success:
                self._spawn_failures += 1
                logger.warning(f"[WARM_POOL] Failed to spawn warm {role} agent ({i+1}/{needed})")
            else:
                self._total_spawned += 1
    
    def _count_idle_agents(self, pool: "AgentPoolManager", role: str) -> int:
        """Count idle agents of a specific role in pool.
        
        Args:
            pool: AgentPoolManager to check
            role: Role type to count
            
        Returns:
            Number of idle agents
        """
        count = 0
        for agent in pool.agents.values():
            if (
                getattr(agent, 'role_type', None) == role and
                getattr(agent, 'state', None) == AgentStatus.idle
            ):
                count += 1
        return count
    
    async def _spawn_warm_agent(self, pool: "AgentPoolManager", role: str) -> bool:
        """Spawn a warm agent without project assignment.
        
        Args:
            pool: AgentPoolManager to spawn in
            role: Role type to spawn
            
        Returns:
            True if spawned successfully
        """
        from sqlmodel import Session
        from app.core.db import engine
        from app.services.persona_service import PersonaService
        from app.services.agent_service import AgentService
        from app.api.routes.agent_management import ensure_role_class_map
        
        try:
            role_class_map = ensure_role_class_map()
            role_class = role_class_map.get(role)
            
            if not role_class:
                logger.error(f"[WARM_POOL] Unknown role type: {role}")
                return False
            
            with Session(engine) as session:
                persona_service = PersonaService(session)
                agent_service = AgentService(session)
                
                # Get a persona for this role
                persona = persona_service.get_random_persona_for_role(
                    role_type=role,
                    exclude_ids=[]
                )
                
                if not persona:
                    logger.error(f"[WARM_POOL] No persona found for role {role}")
                    return False
                
                # Create agent without project (warm agent)
                # project_id=None indicates this is a warm agent
                db_agent = agent_service.create_from_template(
                    project_id=None,  # Warm agent - no project yet
                    persona_template=persona,
                )
                
                agent_id = db_agent.id
                
                logger.debug(
                    f"[WARM_POOL] Created warm agent {db_agent.human_name} ({role})"
                )
            
            # Spawn via pool manager
            success = await pool.spawn_agent(
                agent_id=agent_id,
                role_class=role_class,
                heartbeat_interval=30,
                max_idle_time=600,  # Longer idle time for warm agents
            )
            
            if success:
                logger.info(
                    f"[WARM_POOL] Spawned warm {role} agent: {db_agent.human_name}"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"[WARM_POOL] Error spawning warm agent: {e}", exc_info=True)
            return False
    
    async def get_warm_agent(self, role: str) -> Optional[UUID]:
        """Get an available warm agent for a role.
        
        This is called when a task needs an agent and can use a warm one.
        
        Args:
            role: Role type needed
            
        Returns:
            Agent UUID if warm agent available, None otherwise
        """
        pool_name = f"{role}_pool"
        pool = self.registry.get(pool_name) or self.registry.get("universal_pool")
        
        if not pool:
            return None
        
        # Find an idle warm agent (project_id is None)
        for agent_id, agent in pool.agents.items():
            if (
                getattr(agent, 'role_type', None) == role and
                getattr(agent, 'state', None) == AgentStatus.idle and
                getattr(agent, 'project_id', 'not_none') is None
            ):
                return agent_id
        
        return None
    
    async def assign_warm_agent(
        self,
        agent_id: UUID,
        project_id: UUID,
    ) -> bool:
        """Assign a warm agent to a project.
        
        Called when a warm agent is selected to handle a task.
        
        Args:
            agent_id: Warm agent UUID
            project_id: Project to assign to
            
        Returns:
            True if assigned successfully
        """
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Agent
        
        try:
            with Session(engine) as session:
                agent = session.get(Agent, agent_id)
                if not agent:
                    logger.error(f"[WARM_POOL] Agent {agent_id} not found")
                    return False
                
                if agent.project_id is not None:
                    logger.warning(
                        f"[WARM_POOL] Agent {agent_id} already assigned to project"
                    )
                    return False
                
                agent.project_id = project_id
                session.add(agent)
                session.commit()
                
                logger.info(
                    f"[WARM_POOL] Assigned warm agent {agent.human_name} to project {project_id}"
                )
                return True
                
        except Exception as e:
            logger.error(f"[WARM_POOL] Error assigning warm agent: {e}", exc_info=True)
            return False
    
    def update_config(self, min_agents_config: Dict[str, int]) -> None:
        """Update minimum agents configuration.
        
        Args:
            min_agents_config: New configuration
        """
        old_config = self.min_agents.copy()
        self.min_agents = min_agents_config
        logger.info(f"[WARM_POOL] Updated config: {old_config} -> {min_agents_config}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get warm pool status.
        
        Returns:
            Status dictionary
        """
        # Count current warm agents per role
        current_counts: Dict[str, int] = {}
        
        for role in self.min_agents.keys():
            pool_name = f"{role}_pool"
            pool = self.registry.get(pool_name) or self.registry.get("universal_pool")
            
            if pool:
                current_counts[role] = self._count_idle_agents(pool, role)
            else:
                current_counts[role] = 0
        
        return {
            "enabled": self.enabled,
            "running": self._running,
            "check_interval": self.check_interval,
            "min_agents_config": self.min_agents,
            "current_idle_counts": current_counts,
            "total_spawned": self._total_spawned,
            "spawn_failures": self._spawn_failures,
            "last_check": self._last_check.isoformat() if self._last_check else None,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get warm pool statistics.
        
        Returns:
            Statistics dictionary
        """
        status = self.get_status()
        
        # Calculate health
        total_required = sum(self.min_agents.values())
        total_available = sum(status["current_idle_counts"].values())
        
        if total_required == 0:
            health = 100.0
        else:
            health = min(100.0, (total_available / total_required) * 100)
        
        return {
            **status,
            "health_percentage": round(health, 1),
            "total_required": total_required,
            "total_available": total_available,
            "deficit": max(0, total_required - total_available),
        }


# Singleton instance
_warm_pool_manager: Optional[WarmPoolManager] = None


def get_warm_pool_manager() -> Optional[WarmPoolManager]:
    """Get singleton WarmPoolManager instance.
    
    Returns:
        WarmPoolManager instance or None if not initialized
    """
    return _warm_pool_manager


def init_warm_pool_manager(
    manager_registry: Dict[str, "AgentPoolManager"],
    min_agents_config: Optional[Dict[str, int]] = None,
    check_interval: Optional[int] = None,
    enabled: Optional[bool] = None,
) -> WarmPoolManager:
    """Initialize warm pool manager singleton.
    
    Args:
        manager_registry: Dict of pool managers
        min_agents_config: Minimum agents per role (uses settings default)
        check_interval: Check interval (uses settings default)
        enabled: Whether enabled (uses settings default)
        
    Returns:
        WarmPoolManager instance
    """
    global _warm_pool_manager
    
    from app.core.config import settings
    
    if min_agents_config is None:
        min_agents_config = getattr(settings, 'WARM_POOL_MIN_AGENTS', {
            "team_leader": 1,
            "developer": 2,
            "tester": 1,
            "business_analyst": 1,
        })
    
    if check_interval is None:
        check_interval = getattr(settings, 'WARM_POOL_CHECK_INTERVAL', 30)
    
    if enabled is None:
        enabled = getattr(settings, 'WARM_POOL_ENABLED', True)
    
    _warm_pool_manager = WarmPoolManager(
        manager_registry=manager_registry,
        min_agents_config=min_agents_config,
        check_interval=check_interval,
        enabled=enabled,
    )
    
    return _warm_pool_manager
