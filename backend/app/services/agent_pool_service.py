"""Agent Pool Service -Agent pool operations."""

from typing import Optional, Dict, Type
from uuid import UUID
import logging
from sqlmodel import Session, select

from app.agents.core.agent_pool_manager import AgentPoolManager
from app.services.singletons import get_pool_registry

logger = logging.getLogger(__name__)

class AgentPoolService:
    """Service for agent pool operations."""

    @staticmethod
    def get_role_class_map() -> Dict[str, Type]:
        """Get role class mapping with lazy imports.
        """
        from app.agents.business_analyst import BusinessAnalyst
        from app.agents.developer import Developer
        from app.agents.team_leader import TeamLeader
        from app.agents.tester import Tester

        return {
            "team_leader": TeamLeader,
            "developer": Developer,
            "tester": Tester,
            "business_analyst": BusinessAnalyst,
        }

    @staticmethod
    def get_available_pool(role_type: Optional[str] = None) -> Optional[AgentPoolManager]:
        """Get best available pool manager based on priority and load.
        
        """
        from app.models import AgentPool
        from app.core.db import engine
        
        registry = get_pool_registry()
        if not registry:
            return None
        
        # Query ALL active pools from DB
        with Session(engine) as session:
            statement = select(AgentPool).where(AgentPool.is_active == True)
            db_pools = {p.pool_name: p for p in session.exec(statement).all()}
        
        # Build candidate list with metrics
        candidates = []
        for pool_name, manager in registry.items():
            db_pool = db_pools.get(pool_name)
            if not db_pool:
                continue  # Pool not in DB or not active
            
            current_agents = len(manager.agents)
            if current_agents >= manager.max_agents:
                continue  # Pool at capacity
            
            # Calculate load (0.0 to 1.0)
            load = current_agents / manager.max_agents if manager.max_agents > 0 else 1.0
            
            candidates.append({
                "manager": manager,
                "priority": db_pool.priority,
                "load": load,
                "current_agents": current_agents,
            })
        
        if not candidates:
            logger.warning("No available pool (all pools at capacity or inactive)")
            return None
        
        # Sort by: priority (asc), load (asc)
        candidates.sort(key=lambda x: (x["priority"], x["load"]))
        
        best = candidates[0]
        logger.info(
            f"Selected pool '{best['manager'].pool_name}' "
            f"(priority={best['priority']}, load={best['load']:.1%}, agents={best['current_agents']})"
        )
        
        return best["manager"]

    @staticmethod
    def find_pool_for_agent(agent_id: UUID) -> Optional[AgentPoolManager]:
        """Find which pool contains the given agent.
        Searches all pools to find the agent. Use this when you need to
        send signals to a specific agent but don't know which pool it's in.
        """
        registry = get_pool_registry()
        for pool_name, manager in registry.items():
            if agent_id in manager.agents:
                logger.debug(f"Agent {agent_id} found in pool '{pool_name}'")
                return manager
        
        logger.debug(f"Agent {agent_id} not found in any pool")
        return None

    @staticmethod
    def ensure_role_class_map() -> Dict[str, Type]:
        """Ensure role class map is loaded (convenience method)."""
        return AgentPoolService.get_role_class_map()
