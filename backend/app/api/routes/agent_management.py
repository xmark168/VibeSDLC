"""Agent lifecycle management API endpoints.

This module provides REST API endpoints for:
- Creating and managing agent pools
- Spawning and terminating agents
- Monitoring agent health and performance
- Viewing system-wide statistics
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select, update

from app.api.deps import get_current_user, get_db, SessionDep
from app.models import User, Agent, AgentStatus, AgentExecution, AgentExecutionStatus
from app.agents.core import (
    AgentPool,
    AgentPoolConfig,
    AgentMonitor,
    get_agent_monitor,
)
from app.agents.core.agent_pool_manager import AgentPoolManager
from app.agents.core.simple_pool_manager import SimplifiedAgentPoolManager
from app.agents.core.redis_client import init_redis, close_redis, get_redis_client
from app.agents.core.name_generator import generate_agent_name, get_display_name
from app.core.config import settings



router = APIRouter(prefix="/agents", tags=["agent-management"])


# ===== Schemas =====

class PoolConfigSchema(BaseModel):
    """Pool configuration schema."""
    max_agents: int = Field(default=10, ge=1)
    health_check_interval: int = Field(default=60, ge=10)


class CreatePoolRequest(BaseModel):
    """Request to create agent pool."""
    role_type: str = Field(..., description="Role type: team_leader, business_analyst, developer, tester")
    pool_name: str = Field(..., description="Unique pool name")
    config: Optional[PoolConfigSchema] = None


class SpawnAgentRequest(BaseModel):
    """Request to spawn agent."""
    project_id: UUID = Field(..., description="Project ID to assign agent to")
    role_type: str = Field(..., description="Role type: team_leader, business_analyst, developer, tester")
    pool_name: str = Field(..., description="Pool name")
    heartbeat_interval: int = Field(default=30, ge=10)
    max_idle_time: int = Field(default=300, ge=60)


class TerminateAgentRequest(BaseModel):
    """Request to terminate agent."""
    pool_name: str = Field(..., description="Pool name")
    agent_id: UUID = Field(..., description="Agent ID to terminate")
    graceful: bool = Field(default=True, description="Graceful shutdown")


class PoolResponse(BaseModel):
    """Pool information response (flexible for both manager types)."""
    pool_name: str
    manager_type: Optional[str] = None  # "simplified" or "multiprocessing"
    role_class: Optional[str] = None  # May not exist in simplified manager
    total_agents: int
    active_agents: int
    busy_agents: int
    idle_agents: int
    total_spawned: int
    total_terminated: int
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    success_rate: float = 0.0
    load: float = 0.0
    created_at: str
    manager_uptime_seconds: Optional[float] = None


class SystemStatsResponse(BaseModel):
    """System statistics response."""
    uptime_seconds: float
    total_pools: int
    total_agents: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    recent_alerts: int


# ===== Global Manager Registry =====

# Manager registry - can hold either AgentPoolManager (old) or SimplifiedAgentPoolManager (new)
_manager_registry: Dict[str, Any] = {}

# Role class mapping - lazy loaded to avoid circular imports
def get_role_class_map():
    """Get role class mapping with lazy imports."""
    from app.agents.team_leader import TeamLeader
    from app.agents.roles.developer import Developer
    from app.agents.roles.tester import Tester
    from app.agents.roles.business_analyst import BusinessAnalyst
    
    return {
        "team_leader": TeamLeader,
        "developer": Developer,
        "tester": Tester,
        "business_analyst": BusinessAnalyst,
    }

ROLE_CLASS_MAP = None  # Will be lazy loaded


def ensure_role_class_map():
    """Ensure ROLE_CLASS_MAP is loaded (lazy init helper)."""
    global ROLE_CLASS_MAP
    if ROLE_CLASS_MAP is None:
        ROLE_CLASS_MAP = get_role_class_map()
    return ROLE_CLASS_MAP


async def initialize_default_pools() -> None:
    """Initialize UNIVERSAL agent pool.

    Supports two modes:
    1. NEW (simplified): Single-process in-memory management (no multiprocessing, no Redis)
    2. OLD (complex): Multiprocessing with Redis coordination

    Mode is controlled by settings.USE_SIMPLIFIED_AGENT_POOL feature flag.
    """
    import logging
    from sqlmodel import Session, select
    from app.core.db import engine

    logger = logging.getLogger(__name__)
    global ROLE_CLASS_MAP
    
    # Lazy load role class map
    if ROLE_CLASS_MAP is None:
        ROLE_CLASS_MAP = get_role_class_map()

    # Check which mode to use
    use_simplified = settings.USE_SIMPLIFIED_AGENT_POOL

    if use_simplified:
        logger.info("🚀 Using SIMPLIFIED agent pool manager (optimized, no multiprocessing)")
        await _initialize_simplified_pool(logger, ROLE_CLASS_MAP)
    else:
        logger.info("⚙️  Using OLD multiprocessing agent pool manager (complex, Redis-based)")
        await _initialize_multiprocessing_pool(logger, ROLE_CLASS_MAP)


async def _initialize_simplified_pool(logger, role_class_map) -> None:
    """Initialize simplified in-memory pool manager."""
    from sqlmodel import Session, select
    from app.core.db import engine

    pool_name = "universal_pool"

    # Skip if manager already exists
    if pool_name in _manager_registry:
        logger.info(f"Universal pool already exists, skipping")
        return

    try:
        # Create simplified manager (no Redis, no multiprocessing)
        manager = SimplifiedAgentPoolManager(
            pool_name=pool_name,
            max_agents=100,  # Higher limit since no process overhead
            health_check_interval=60,
        )

        # Start manager
        if await manager.start():
            _manager_registry[pool_name] = manager
            logger.info(f"✓ Created SIMPLIFIED pool: {pool_name} (supports all role types)")

            # Restore agents from database
            await _restore_agents_simplified(logger, manager, role_class_map)

        else:
            logger.error(f"✗ Failed to start simplified manager: {pool_name}")

    except Exception as e:
        logger.error(f"✗ Error creating simplified pool '{pool_name}': {e}", exc_info=True)


async def _restore_agents_simplified(logger, manager, role_class_map) -> None:
    """Restore agents for simplified manager."""
    from sqlmodel import Session, select
    from app.core.db import engine

    with Session(engine) as db_session:
        # Reset transient states
        reset_states = [
            AgentStatus.starting,
            AgentStatus.stopping,
            AgentStatus.busy,
            AgentStatus.error,
            AgentStatus.terminated,
        ]
        reset_stmt = (
            update(Agent)
            .where(Agent.status.in_(reset_states))
            .values(status=AgentStatus.idle)
        )
        reset_result = db_session.exec(reset_stmt)
        db_session.commit()

        if reset_result.rowcount > 0:
            logger.info(f"Auto-reset {reset_result.rowcount} agents from problematic states to idle")

        # Query agents to restore
        agents_query = select(Agent).where(
            Agent.status.in_([AgentStatus.idle, AgentStatus.stopped])
        )
        db_agents = db_session.exec(agents_query).all()

        logger.info(f"Restoring {len(db_agents)} agents...")

        # Spawn agents
        for db_agent in db_agents:
            try:
                role_class = role_class_map.get(db_agent.role_type)
                if not role_class:
                    logger.warning(f"  ✗ Unknown role_type '{db_agent.role_type}' for agent {db_agent.human_name}")
                    continue

                success = await manager.spawn_agent(
                    agent_id=db_agent.id,
                    role_class=role_class,
                    heartbeat_interval=30,
                    max_idle_time=300,
                )

                if success:
                    logger.debug(f"  ✓ Restored: {db_agent.human_name} [{db_agent.role_type}]")
                else:
                    logger.warning(f"  ✗ Failed: {db_agent.human_name}")

            except Exception as e:
                logger.error(f"Error restoring {db_agent.human_name}: {e}")

        logger.info(f"📊 Restored {len(db_agents)} agents in simplified pool")


async def _initialize_multiprocessing_pool(logger, role_class_map) -> None:
    """Initialize old multiprocessing pool manager with Redis."""
    from sqlmodel import Session, select
    from app.core.db import engine

    # Initialize Redis (required for multiprocessing mode)
    logger.info("Initializing Redis for multiprocessing agent pools...")
    if not await init_redis():
        raise RuntimeError(
            "Failed to connect to Redis. Redis is required for multiprocessing mode.\n"
            "Please ensure Redis is running: docker-compose up -d redis"
        )

    logger.info("✓ Redis connected successfully")

    # Create ONE universal pool instead of 4 role-specific pools
    pool_name = "universal_pool"

    # Skip if manager already exists
    if pool_name in _manager_registry:
        logger.info(f"Universal pool already exists, skipping")
        return

    try:
        # Create Universal AgentPoolManager (no role_class - accepts all roles)
        manager = AgentPoolManager(
            pool_name=pool_name,
            max_agents_per_process=10,
            heartbeat_interval=30,
        )

        # Start manager
        if await manager.start():
            _manager_registry[pool_name] = manager
            logger.info(f"✓ Created UNIVERSAL pool: {pool_name} (supports all role types)")

            # Restore ALL agents from database (all role types)
            with Session(engine) as db_session:
                # Reset transient states for ALL agents
                reset_states = [
                    AgentStatus.starting,
                    AgentStatus.stopping,
                    AgentStatus.busy,
                    AgentStatus.error,
                    AgentStatus.terminated,
                ]
                reset_stmt = (
                    update(Agent)
                    .where(Agent.status.in_(reset_states))
                    .values(status=AgentStatus.idle)
                )
                reset_result = db_session.exec(reset_stmt)
                db_session.commit()

                if reset_result.rowcount > 0:
                    logger.info(
                        f"Auto-reset {reset_result.rowcount} agents from problematic states to idle"
                    )

                # Query ALL agents to restore (all role types)
                agents_query = select(Agent).where(
                    Agent.status.in_([AgentStatus.idle, AgentStatus.stopped])
                )
                db_agents = db_session.exec(agents_query).all()

                logger.info(
                    f"Restoring {len(db_agents)} agents across all role types "
                    f"(workers will auto-spawn as needed)..."
                )

                # Spawn agents via universal manager
                for db_agent in db_agents:
                    try:
                        # Get role_class for this agent
                        role_class = ROLE_CLASS_MAP.get(db_agent.role_type)
                        if not role_class:
                            logger.warning(
                                f"  ✗ Unknown role_type '{db_agent.role_type}' for agent {db_agent.human_name}"
                            )
                            continue

                        success = await manager.spawn_agent(
                            agent_id=db_agent.id,
                            role_class=role_class,
                            heartbeat_interval=30,
                            max_idle_time=300,
                        )

                        if success:
                            db_agent.status = AgentStatus.idle
                            db_session.add(db_agent)
                            logger.debug(f"  ✓ Queued: {db_agent.human_name} [{db_agent.role_type}]")
                        else:
                            logger.warning(f"  ✗ Failed: {db_agent.human_name}")

                    except Exception as e:
                        logger.error(f"Error restoring {db_agent.human_name}: {e}")

                db_session.commit()

                logger.info(f"📊 Queued {len(db_agents)} agents for restoration in universal pool")

        else:
            logger.error(f"✗ Failed to start manager: {pool_name}")

    except Exception as e:
        logger.error(f"✗ Error creating pool '{pool_name}': {e}", exc_info=True)


def get_manager(pool_name: str) -> AgentPoolManager:
    """Get pool manager by name or raise 404.

    Args:
        pool_name: Pool name

    Returns:
        Agent pool manager

    Raises:
        HTTPException: If manager not found
    """
    manager = _manager_registry.get(pool_name)
    if not manager:
        raise HTTPException(status_code=404, detail=f"Pool manager '{pool_name}' not found")
    return manager


# ===== Pool Management Endpoints =====

@router.post("/pools", response_model=PoolResponse)
async def create_pool(
    request: CreatePoolRequest,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Create a new agent pool manager.

    Creates and starts a new agent pool manager for the specified role type.
    The manager will automatically spawn worker processes and manage agent lifecycle.
    """
    # Ensure role class map is loaded
    role_class_map = ensure_role_class_map()
    
    # Validate role type
    if request.role_type not in role_class_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role_type. Must be one of: {list(role_class_map.keys())}"
        )

    # Check if pool manager already exists
    if request.pool_name in _manager_registry:
        raise HTTPException(status_code=400, detail=f"Pool manager '{request.pool_name}' already exists")

    # Extract max_agents if provided (default 10)
    max_agents_per_process = 10
    if request.config:
        max_agents_per_process = request.config.max_agents

    # Create pool manager
    role_class = role_class_map[request.role_type]
    manager = AgentPoolManager(
        pool_name=request.pool_name,
        role_class=role_class,
        max_agents_per_process=max_agents_per_process,
        heartbeat_interval=30,
    )

    # Start manager
    if not await manager.start():
        raise HTTPException(status_code=500, detail="Failed to start pool manager")

    # Register manager
    _manager_registry[request.pool_name] = manager

    # Return manager stats
    stats = await manager.get_stats()
    return PoolResponse(**stats)


@router.get("/pools", response_model=List[PoolResponse])
async def list_pools(
    current_user: User = Depends(get_current_user),
) -> Any:
    """List all agent pool managers and their statistics."""
    stats_list = []
    for manager in _manager_registry.values():
        stats = await manager.get_stats()
        stats_list.append(PoolResponse(**stats))
    return stats_list


@router.get("/pools/{pool_name}", response_model=PoolResponse)
async def get_pool_stats(
    pool_name: str,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get statistics for a specific pool."""
    manager = get_manager(pool_name)
    stats = await manager.get_stats()
    return PoolResponse(**stats)


@router.delete("/pools/{pool_name}")
async def delete_pool(
    pool_name: str,
    graceful: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Stop and delete an agent pool manager and all its workers."""
    manager = get_manager(pool_name)

    # Stop manager and all workers
    if not await manager.stop(graceful=graceful):
        raise HTTPException(status_code=500, detail="Failed to stop pool manager")

    # Remove from registry
    del _manager_registry[pool_name]

    return {"message": f"Pool manager '{pool_name}' and all workers deleted successfully"}


# ===== Agent Management Endpoints =====

@router.post("/spawn")
async def spawn_agent(
    request: SpawnAgentRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Spawn a new agent in the specified pool and persist to database.

    Works with both simplified and multiprocessing pool managers.
    The manager type is determined by the USE_SIMPLIFIED_AGENT_POOL setting.
    """
    # Ensure role class map is loaded
    role_class_map = ensure_role_class_map()
    
    # Validate role type
    if request.role_type not in role_class_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role_type. Must be one of: {list(role_class_map.keys())}"
        )

    # Get existing agent names for this project/role to avoid duplicates
    existing_agents = session.exec(
        select(Agent).where(
            Agent.project_id == request.project_id,
            Agent.role_type == request.role_type
        )
    ).all()
    existing_names = [a.human_name for a in existing_agents]

    # Generate unique human name
    human_name = generate_agent_name(request.role_type, existing_names)
    display_name = get_display_name(human_name, request.role_type)

    # Create agent in database first
    db_agent = Agent(
        project_id=request.project_id,
        name=display_name,
        human_name=human_name,
        role_type=request.role_type,
        agent_type=request.role_type,
        status=AgentStatus.idle,
    )
    session.add(db_agent)
    session.commit()
    session.refresh(db_agent)

    # Get universal pool manager
    pool_name = "universal_pool"
    manager = get_manager(pool_name)

    # Get role_class for this agent
    role_class = role_class_map[request.role_type]

    # Spawn via manager (works with both simplified and multiprocessing)
    success = await manager.spawn_agent(
        agent_id=db_agent.id,
        role_class=role_class,
        heartbeat_interval=request.heartbeat_interval,
        max_idle_time=request.max_idle_time,
    )

    if not success:
        # Rollback database entry if spawn fails
        session.delete(db_agent)
        session.commit()
        raise HTTPException(status_code=500, detail="Failed to spawn agent")

    return {
        "agent_id": str(db_agent.id),
        "human_name": human_name,
        "display_name": display_name,
        "role_type": request.role_type,
        "project_id": str(request.project_id),
        "pool_name": pool_name,  # Always "universal_pool"
        "state": "spawning",
        "created_at": db_agent.created_at.isoformat(),
    }


@router.post("/terminate")
async def terminate_agent(
    request: TerminateAgentRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Terminate an agent in the specified pool and update database.

    Works with both simplified and multiprocessing pool managers.
    """
    manager = get_manager(request.pool_name)

    # Terminate via manager (works with both simplified and multiprocessing)
    success = await manager.terminate_agent(request.agent_id, graceful=request.graceful)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to terminate agent")

    # Update agent status in database
    db_agent = session.get(Agent, request.agent_id)
    if db_agent:
        db_agent.status = AgentStatus.terminated
        session.add(db_agent)
        session.commit()

    return {
        "message": f"Agent {request.agent_id} terminated successfully",
        "pool_name": request.pool_name,
    }


@router.get("/project/{project_id}")
async def get_project_agents(
    project_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get all agents for a specific project."""
    agents = session.exec(
        select(Agent).where(Agent.project_id == project_id)
    ).all()

    return [
        {
            "id": str(agent.id),
            "name": agent.name,
            "human_name": agent.human_name,
            "role_type": agent.role_type,
            "status": agent.status.value,
            "project_id": str(agent.project_id),
            "created_at": agent.created_at.isoformat(),
        }
        for agent in agents
    ]


# ===== Monitoring Endpoints =====
# NOTE: These must be defined BEFORE /{agent_id}/* routes to avoid catch-all matching

@router.get("/monitor/system", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get system-wide agent statistics from all pool managers."""
    from app.agents.core.registry import ProcessRegistry, AgentRegistry
    from datetime import datetime, timezone

    redis = get_redis_client()
    agent_registry = AgentRegistry(redis_client=redis)
    process_registry = ProcessRegistry(redis_client=redis)

    # Aggregate stats from all pool managers
    total_agents = 0
    total_processes = 0
    total_capacity = 0

    for pool_name, manager in _manager_registry.items():
        stats = await manager.get_stats()
        total_agents += stats.get("agent_count", 0)
        total_processes += stats.get("process_count", 0)
        total_capacity += stats.get("total_capacity", 0)

    return SystemStatsResponse(
        uptime_seconds=0,  # Can track startup time if needed
        total_pools=len(_manager_registry),
        total_agents=total_agents,
        total_executions=0,  # Would need to aggregate from DB
        successful_executions=0,
        failed_executions=0,
        success_rate=0.0,
        recent_alerts=0,
    )


@router.get("/monitor/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get comprehensive dashboard data for monitoring multiprocessing pools."""
    from datetime import datetime, timezone

    # Get stats from all managers
    pools_data = {}
    for pool_name, manager in _manager_registry.items():
        pools_data[pool_name] = await manager.get_stats()

    return {
        "pools": pools_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "multiprocessing",
    }


@router.get("/monitor/alerts")
async def get_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get recent monitoring alerts.

    Note: In multiprocessing mode, alerts would need to be stored in Redis.
    This is a placeholder implementation.
    """
    return []


# ===== Metrics Endpoints for Analytics =====

@router.get("/metrics/timeseries")
async def get_metrics_timeseries(
    session: SessionDep,
    metric_type: str = Query(..., description="Metric type: utilization, executions, tokens, success_rate"),
    time_range: str = Query(default="24h", description="Time range: 1h, 6h, 24h, 7d, 30d"),
    interval: str = Query(default="auto", description="Data point interval: auto, 5m, 15m, 1h, 1d"),
    pool_name: Optional[str] = Query(default=None, description="Filter by pool name"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get time-series metrics data for visualizations.

    Returns historical metrics snapshots for creating charts and graphs.
    """
    from datetime import datetime, timezone, timedelta
    from app.models import AgentMetricsSnapshot

    # Parse time range
    time_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    if time_range not in time_map:
        raise HTTPException(status_code=400, detail=f"Invalid time_range: {time_range}")

    cutoff_time = datetime.now(timezone.utc) - time_map[time_range]

    # Build query
    query = select(AgentMetricsSnapshot).where(
        AgentMetricsSnapshot.snapshot_timestamp >= cutoff_time
    ).order_by(AgentMetricsSnapshot.snapshot_timestamp.asc())

    if pool_name:
        query = query.where(AgentMetricsSnapshot.pool_name == pool_name)

    snapshots = session.exec(query).all()

    # Format data based on metric type
    data_points = []
    for snapshot in snapshots:
        point = {
            "timestamp": snapshot.snapshot_timestamp.isoformat(),
            "pool_name": snapshot.pool_name,
        }

        if metric_type == "utilization":
            point["idle"] = snapshot.idle_agents
            point["busy"] = snapshot.busy_agents
            point["error"] = snapshot.error_agents
            point["total"] = snapshot.total_agents
            point["utilization_pct"] = snapshot.utilization_percentage or 0
        elif metric_type == "executions":
            point["total"] = snapshot.total_executions
            point["successful"] = snapshot.successful_executions
            point["failed"] = snapshot.failed_executions
            point["success_rate"] = (
                (snapshot.successful_executions / snapshot.total_executions * 100)
                if snapshot.total_executions > 0 else 0
            )
        elif metric_type == "tokens":
            point["tokens"] = snapshot.total_tokens
            point["llm_calls"] = snapshot.total_llm_calls
            point["avg_duration_ms"] = snapshot.avg_execution_duration_ms
        elif metric_type == "success_rate":
            point["total"] = snapshot.total_executions
            point["successful"] = snapshot.successful_executions
            point["failed"] = snapshot.failed_executions
            point["success_rate"] = (
                (snapshot.successful_executions / snapshot.total_executions * 100)
                if snapshot.total_executions > 0 else 0
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid metric_type: {metric_type}")

        data_points.append(point)

    return {
        "metric_type": metric_type,
        "time_range": time_range,
        "interval": interval,
        "pool_name": pool_name,
        "data": data_points,
        "count": len(data_points),
    }


@router.get("/metrics/aggregated")
async def get_metrics_aggregated(
    session: SessionDep,
    time_range: str = Query(default="24h", description="Time range: 1h, 6h, 24h, 7d, 30d"),
    group_by: str = Query(default="pool", description="Group by: pool, hour, day"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get aggregated metrics statistics.

    Returns summarized metrics grouped by pool, time period, or agent type.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import and_, func
    from app.models import AgentMetricsSnapshot

    # Parse time range
    time_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    if time_range not in time_map:
        raise HTTPException(status_code=400, detail=f"Invalid time_range: {time_range}")

    cutoff_time = datetime.now(timezone.utc) - time_map[time_range]

    # Build aggregation query based on group_by
    if group_by == "pool":
        # Aggregate by pool name
        query = select(
            AgentMetricsSnapshot.pool_name,
            func.avg(AgentMetricsSnapshot.total_agents).label("avg_agents"),
            func.avg(AgentMetricsSnapshot.utilization_percentage).label("avg_utilization"),
            func.sum(AgentMetricsSnapshot.total_executions).label("total_executions"),
            func.sum(AgentMetricsSnapshot.successful_executions).label("successful_executions"),
            func.sum(AgentMetricsSnapshot.failed_executions).label("failed_executions"),
            func.sum(AgentMetricsSnapshot.total_tokens).label("total_tokens"),
            func.sum(AgentMetricsSnapshot.total_llm_calls).label("total_llm_calls"),
            func.avg(AgentMetricsSnapshot.avg_execution_duration_ms).label("avg_duration_ms"),
        ).where(
            AgentMetricsSnapshot.snapshot_timestamp >= cutoff_time
        ).group_by(
            AgentMetricsSnapshot.pool_name
        )

        results = session.exec(query).all()

        aggregated_data = []
        for row in results:
            total_exec = row.total_executions or 0
            success_rate = (
                (row.successful_executions / total_exec * 100) if total_exec > 0 else 0
            )

            aggregated_data.append({
                "pool_name": row.pool_name,
                "avg_agents": round(row.avg_agents or 0, 2),
                "avg_utilization": round(row.avg_utilization or 0, 2),
                "total_executions": total_exec,
                "successful_executions": row.successful_executions or 0,
                "failed_executions": row.failed_executions or 0,
                "success_rate": round(success_rate, 2),
                "total_tokens": row.total_tokens or 0,
                "total_llm_calls": row.total_llm_calls or 0,
                "avg_duration_ms": round(row.avg_duration_ms or 0, 2),
            })

        return {
            "group_by": group_by,
            "time_range": time_range,
            "data": aggregated_data,
            "count": len(aggregated_data),
        }

    elif group_by in ["hour", "day"]:
        # Time-based aggregation
        # Note: This is simplified - production code would use date_trunc
        query = select(AgentMetricsSnapshot).where(
            AgentMetricsSnapshot.snapshot_timestamp >= cutoff_time
        ).order_by(AgentMetricsSnapshot.snapshot_timestamp.asc())

        snapshots = session.exec(query).all()

        # Group snapshots by time bucket
        # Simplified implementation - just return raw snapshots for now
        return {
            "group_by": group_by,
            "time_range": time_range,
            "data": [
                {
                    "timestamp": s.snapshot_timestamp.isoformat(),
                    "pool_name": s.pool_name,
                    "total_agents": s.total_agents,
                    "total_executions": s.total_executions,
                    "total_tokens": s.total_tokens,
                }
                for s in snapshots
            ],
            "count": len(snapshots),
        }

    else:
        raise HTTPException(status_code=400, detail=f"Invalid group_by: {group_by}")


@router.get("/metrics/processes")
async def get_process_metrics(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get current worker process metrics.

    Returns real-time process distribution, capacity, and utilization.
    """
    from app.agents.core.registry import ProcessRegistry, AgentRegistry

    redis = get_redis_client()
    process_registry = ProcessRegistry(redis_client=redis)
    agent_registry = AgentRegistry(redis_client=redis)

    all_processes = []

    for pool_name in _manager_registry.keys():
        # Get processes for this pool
        process_ids = await process_registry.get_pool_processes(pool_name)

        for process_id in process_ids:
            process_info = await process_registry.get_info(process_id)
            if process_info:
                # Get agents in this process
                agent_count = len(process_info.get("agents", []))
                max_agents = process_info.get("max_agents", 10)

                all_processes.append({
                    "process_id": process_id,
                    "pool_name": pool_name,
                    "agent_count": agent_count,
                    "max_agents": max_agents,
                    "utilization": (agent_count / max_agents * 100) if max_agents > 0 else 0,
                    "pid": process_info.get("pid"),
                    "status": process_info.get("status", "unknown"),
                    "started_at": process_info.get("started_at"),
                })

    # Calculate summary
    total_processes = len(all_processes)
    total_capacity = sum(p["max_agents"] for p in all_processes)
    used_capacity = sum(p["agent_count"] for p in all_processes)
    avg_utilization = (used_capacity / total_capacity * 100) if total_capacity > 0 else 0

    return {
        "summary": {
            "total_processes": total_processes,
            "total_capacity": total_capacity,
            "used_capacity": used_capacity,
            "available_capacity": total_capacity - used_capacity,
            "avg_utilization": round(avg_utilization, 2),
        },
        "processes": all_processes,
    }


@router.get("/metrics/tokens")
async def get_token_metrics(
    session: SessionDep,
    time_range: str = Query(default="24h", description="Time range: 1h, 6h, 24h, 7d, 30d"),
    group_by: str = Query(default="pool", description="Group by: pool, agent_type"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get token usage analytics.

    Returns token consumption, LLM call counts, and cost estimates.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import and_, func
    from app.models import AgentMetricsSnapshot

    # Parse time range
    time_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    if time_range not in time_map:
        raise HTTPException(status_code=400, detail=f"Invalid time_range: {time_range}")

    cutoff_time = datetime.now(timezone.utc) - time_map[time_range]

    # Aggregate token usage by pool
    query = select(
        AgentMetricsSnapshot.pool_name,
        func.sum(AgentMetricsSnapshot.total_tokens).label("total_tokens"),
        func.sum(AgentMetricsSnapshot.total_llm_calls).label("total_llm_calls"),
        func.avg(AgentMetricsSnapshot.avg_execution_duration_ms).label("avg_duration_ms"),
        func.count(AgentMetricsSnapshot.id).label("snapshot_count"),
    ).where(
        AgentMetricsSnapshot.snapshot_timestamp >= cutoff_time
    ).group_by(
        AgentMetricsSnapshot.pool_name
    )

    results = session.exec(query).all()

    token_data = []
    total_tokens = 0
    total_llm_calls = 0

    for row in results:
        tokens = row.total_tokens or 0
        llm_calls = row.total_llm_calls or 0

        # Rough cost estimate (using GPT-4 pricing as example: $0.03/1K tokens)
        # This should be configurable based on actual model used
        estimated_cost = (tokens / 1000) * 0.03

        token_data.append({
            "pool_name": row.pool_name,
            "total_tokens": tokens,
            "total_llm_calls": llm_calls,
            "avg_tokens_per_call": round(tokens / llm_calls, 2) if llm_calls > 0 else 0,
            "avg_duration_ms": round(row.avg_duration_ms or 0, 2),
            "estimated_cost_usd": round(estimated_cost, 4),
        })

        total_tokens += tokens
        total_llm_calls += llm_calls

    return {
        "time_range": time_range,
        "group_by": group_by,
        "summary": {
            "total_tokens": total_tokens,
            "total_llm_calls": total_llm_calls,
            "avg_tokens_per_call": round(total_tokens / total_llm_calls, 2) if total_llm_calls > 0 else 0,
            "estimated_total_cost_usd": round((total_tokens / 1000) * 0.03, 4),
        },
        "data": token_data,
        "count": len(token_data),
    }


@router.get("/health")
async def get_all_agent_health(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get health status of all agents across all pools.

    Returns agent states from Redis registry (agents run in worker processes).
    """
    from app.agents.core.registry import AgentRegistry

    redis = get_redis_client()
    agent_registry = AgentRegistry(redis_client=redis)

    health_data = {}
    for pool_name in _manager_registry.keys():
        # Get agents for this pool from Redis
        agent_ids = await agent_registry.get_pool_agents(pool_name)

        pool_health = []
        for agent_id_str in agent_ids:
            from uuid import UUID
            agent_info = await agent_registry.get_info(UUID(agent_id_str))
            if agent_info:
                pool_health.append({
                    "agent_id": agent_id_str,
                    "status": agent_info.get("status"),
                    "process_id": agent_info.get("process_id"),
                    "role_type": agent_info.get("role_type"),
                })

        health_data[pool_name] = pool_health

    return health_data


# ===== Agent-specific Endpoints (with {agent_id} path parameter) =====
# NOTE: In multiprocessing mode, agents run in separate worker processes.
# Direct agent access is not available. Use database and Redis for agent state.


# ===== Execution History Endpoints =====
# NOTE: Specific routes like /stats/summary must come BEFORE /{execution_id}

@router.get("/executions")
async def get_executions(
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = Query(default=None, description="Filter by status: pending, running, completed, failed, cancelled"),
    agent_type: Optional[str] = Query(default=None, description="Filter by agent type"),
    project_id: Optional[UUID] = Query(default=None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get agent execution history with optional filters."""
    query = select(AgentExecution).order_by(AgentExecution.created_at.desc())

    # Apply filters
    if status:
        try:
            status_enum = AgentExecutionStatus(status)
            query = query.where(AgentExecution.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if agent_type:
        query = query.where(AgentExecution.agent_type == agent_type)

    if project_id:
        query = query.where(AgentExecution.project_id == project_id)

    query = query.limit(limit)

    executions = session.exec(query).all()

    return [
        {
            "id": str(ex.id),
            "project_id": str(ex.project_id),
            "agent_name": ex.agent_name,
            "agent_type": ex.agent_type,
            "status": ex.status.value,
            "started_at": ex.started_at.isoformat() if ex.started_at else None,
            "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
            "duration_ms": ex.duration_ms,
            "token_used": ex.token_used,
            "llm_calls": ex.llm_calls,
            "error_message": ex.error_message,
            "created_at": ex.created_at.isoformat(),
        }
        for ex in executions
    ]


@router.get("/executions/stats/summary")
async def get_execution_stats(
    session: SessionDep,
    project_id: Optional[UUID] = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get execution statistics summary."""
    from sqlalchemy import func

    query = select(
        AgentExecution.agent_type,
        AgentExecution.status,
        func.count(AgentExecution.id).label("count"),
        func.avg(AgentExecution.duration_ms).label("avg_duration"),
        func.sum(AgentExecution.token_used).label("total_tokens"),
    ).group_by(AgentExecution.agent_type, AgentExecution.status)

    if project_id:
        query = query.where(AgentExecution.project_id == project_id)

    results = session.exec(query).all()

    # Aggregate stats
    stats = {}
    for row in results:
        agent_type = row[0]
        if agent_type not in stats:
            stats[agent_type] = {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "avg_duration_ms": 0,
                "total_tokens": 0,
            }

        stats[agent_type]["total"] += row[2]
        if row[1] == AgentExecutionStatus.COMPLETED:
            stats[agent_type]["completed"] += row[2]
        elif row[1] == AgentExecutionStatus.FAILED:
            stats[agent_type]["failed"] += row[2]

        if row[3]:
            stats[agent_type]["avg_duration_ms"] = float(row[3])
        if row[4]:
            stats[agent_type]["total_tokens"] += row[4]

    return stats


@router.get("/executions/{execution_id}")
async def get_execution_detail(
    execution_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get detailed information about a specific execution."""
    execution = session.get(AgentExecution, execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

    return {
        "id": str(execution.id),
        "project_id": str(execution.project_id),
        "agent_name": execution.agent_name,
        "agent_type": execution.agent_type,
        "status": execution.status.value,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "duration_ms": execution.duration_ms,
        "token_used": execution.token_used,
        "llm_calls": execution.llm_calls,
        "error_message": execution.error_message,
        "error_traceback": execution.error_traceback,
        "result": execution.result,
        "extra_metadata": execution.extra_metadata,
        "created_at": execution.created_at.isoformat(),
        "updated_at": execution.updated_at.isoformat(),
    }


# ===== Lifecycle Management =====

@router.post("/system/start")
async def start_monitoring_system(
    monitor_interval: int = Query(default=30, ge=10),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Start the agent monitoring system."""
    monitor = get_agent_monitor()

    if not await monitor.start(monitor_interval=monitor_interval):
        raise HTTPException(status_code=500, detail="Failed to start monitoring system")

    return {"message": "Monitoring system started successfully"}


@router.post("/system/stop")
async def stop_monitoring_system(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Stop the agent monitoring system."""
    monitor = get_agent_monitor()

    if not await monitor.stop():
        raise HTTPException(status_code=500, detail="Failed to stop monitoring system")

    return {"message": "Monitoring system stopped successfully"}
