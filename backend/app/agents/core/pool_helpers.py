"""Pool helper functions for quick wins: auto-creation, smart selection, etc."""

import logging
from typing import Optional, Dict
from uuid import UUID

from sqlmodel import Session

from app.models import PoolType, AgentPool
from app.services.pool_service import PoolService
from app.agents.core.agent_pool_manager import AgentPoolManager

logger = logging.getLogger(__name__)


def get_pool_load(manager: AgentPoolManager) -> float:
    """Calculate current pool load (0.0 to 1.0)."""
    if manager.max_agents == 0:
        return 0.0
    return len(manager.agents) / manager.max_agents


def should_create_new_pool(
    manager: AgentPoolManager,
    threshold: float = 0.8
) -> bool:
    """Check if pool load exceeds threshold and new pool should be created."""
    load = get_pool_load(manager)
    return load >= threshold


async def create_pool_for_role(
    session: Session,
    role_type: str,
    pool_type: PoolType = PoolType.FREE,
    max_agents: int = 50,
    created_by: Optional[UUID] = None,
) -> Optional[AgentPool]:
    """
    Create a new role-specific pool in DB.
    
    Args:
        session: Database session
        role_type: Agent role type (e.g., "developer", "tester")
        pool_type: FREE or PAID
        max_agents: Maximum agents in pool
        created_by: User ID who created the pool
    
    Returns:
        Created AgentPool or None if failed
    """
    pool_service = PoolService(session)
    
    # Check if pool already exists
    existing_pools = pool_service.get_active_pools(role_type=role_type)
    if existing_pools:
        logger.info(f"Pool for role '{role_type}' already exists")
        return existing_pools[0]
    
    # Generate pool name
    pool_name = f"{role_type}_pool"
    
    try:
        pool = pool_service.create_pool(
            pool_name=pool_name,
            role_type=role_type,
            pool_type=pool_type,
            max_agents=max_agents,
            created_by=created_by,
            auto_created=True,
        )
        logger.info(f"✓ Created new pool for role '{role_type}': {pool_name}")
        return pool
    except Exception as e:
        logger.error(f"Failed to create pool for role '{role_type}': {e}", exc_info=True)
        return None


def get_best_pool_for_agent(
    manager_registry: Dict[str, AgentPoolManager],
    role_type: str,
    prefer_role_pool: bool = True
) -> Optional[AgentPoolManager]:
    """
    Select the best pool for spawning an agent.
    
    Strategy:
    1. If prefer_role_pool=True, try role-specific pool first
    2. Fall back to pool with lowest load
    3. Return None if all pools are full
    
    Args:
        manager_registry: Dict of pool_name -> AgentPoolManager
        role_type: Agent role type
        prefer_role_pool: Prefer role-specific pool if exists
    
    Returns:
        Best AgentPoolManager or None
    """
    if not manager_registry:
        return None
    
    # Try role-specific pool first
    if prefer_role_pool:
        role_pool_name = f"{role_type}_pool"
        if role_pool_name in manager_registry:
            manager = manager_registry[role_pool_name]
            if len(manager.agents) < manager.max_agents:
                logger.debug(f"Selected role-specific pool '{role_pool_name}' for {role_type}")
                return manager
    
    # Find pool with lowest load that has capacity
    best_manager = None
    lowest_load = float('inf')
    
    for manager in manager_registry.values():
        current_agents = len(manager.agents)
        
        # Skip full pools
        if current_agents >= manager.max_agents:
            continue
        
        load = current_agents / manager.max_agents if manager.max_agents > 0 else 0
        
        if load < lowest_load:
            lowest_load = load
            best_manager = manager
    
    if best_manager:
        logger.debug(
            f"Selected pool '{best_manager.pool_name}' with load {lowest_load:.2%} "
            f"for {role_type}"
        )
    else:
        logger.warning(f"All pools are at capacity, cannot spawn {role_type} agent")
    
    return best_manager


async def auto_scale_pools(
    session: Session,
    manager_registry: Dict[str, AgentPoolManager],
    scale_threshold: float = 0.8,
) -> Optional[AgentPool]:
    """
    Auto-create new pool if universal pool is overloaded.
    
    Args:
        session: Database session
        manager_registry: Current pool managers
        scale_threshold: Load threshold to trigger scaling (default 80%)
    
    Returns:
        Newly created pool or None
    """
    universal_pool = manager_registry.get("universal_pool")
    if not universal_pool:
        return None
    
    if not should_create_new_pool(universal_pool, scale_threshold):
        return None
    
    logger.info(
        f"Universal pool load at {get_pool_load(universal_pool):.2%}, "
        f"creating overflow pool"
    )
    
    # Create overflow pool
    pool_service = PoolService(session)
    overflow_count = len([p for p in manager_registry.keys() if "overflow" in p])
    
    pool_name = f"overflow_pool_{overflow_count + 1}"
    
    try:
        pool = pool_service.create_pool(
            pool_name=pool_name,
            role_type=None,  # Universal
            pool_type=PoolType.FREE,
            max_agents=50,  # Smaller than main pool
            auto_created=True,
        )
        logger.info(f"✓ Auto-created overflow pool: {pool_name}")
        return pool
    except Exception as e:
        logger.error(f"Failed to auto-create overflow pool: {e}", exc_info=True)
        return None


def get_pool_statistics(
    manager_registry: Dict[str, AgentPoolManager]
) -> Dict[str, any]:
    """
    Get comprehensive statistics across all pools.
    
    Returns:
        Dict with pool statistics
    """
    total_agents = sum(len(m.agents) for m in manager_registry.values())
    total_capacity = sum(m.max_agents for m in manager_registry.values())
    total_spawned = sum(m.total_spawned for m in manager_registry.values())
    total_terminated = sum(m.total_terminated for m in manager_registry.values())
    
    pool_stats = []
    for name, manager in manager_registry.items():
        pool_stats.append({
            "pool_name": name,
            "current_agents": len(manager.agents),
            "max_agents": manager.max_agents,
            "load": get_pool_load(manager),
            "total_spawned": manager.total_spawned,
            "total_terminated": manager.total_terminated,
        })
    
    return {
        "total_pools": len(manager_registry),
        "total_agents": total_agents,
        "total_capacity": total_capacity,
        "overall_load": total_agents / total_capacity if total_capacity > 0 else 0,
        "total_spawned": total_spawned,
        "total_terminated": total_terminated,
        "pools": pool_stats,
    }
