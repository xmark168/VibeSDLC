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
import asyncio
import json

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, update

from app.api.deps import get_current_user, get_db, SessionDep
from app.models import User, Agent, AgentStatus, AgentExecution, AgentExecutionStatus
from app.agents.core import AgentPoolManager
from app.services.persona_service import PersonaService
from app.services.pool_service import PoolService
from app.core.config import settings
from app.schemas import (
    PoolConfigSchema,
    CreatePoolRequest,
    SpawnAgentRequest,
    TerminateAgentRequest,
    PoolResponse,
    SystemStatsResponse,
    AgentPoolPublic,
    UpdatePoolConfigRequest,
    AgentPoolMetricsPublic,
    CreatePoolRequestExtended,
    ScalePoolRequest,
    PoolSuggestion,
)


router = APIRouter(prefix="/agents", tags=["agent-management"])


# ===== Global Manager Registry =====

# Manager registry - holds AgentPoolManager instances
_manager_registry: Dict[str, AgentPoolManager] = {}

# Role class mapping - lazy loaded to avoid circular imports
def get_role_class_map():
    """Get role class mapping with lazy imports."""
    from app.agents.team_leader import TeamLeader
    from app.agents.developer import Developer
    from app.agents.tester import Tester
    from app.agents.business_analyst import BusinessAnalyst
    
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
    """Initialize UNIVERSAL agent pool with in-memory management.

    Uses AgentPoolManager:
    - Single-process in-memory management
    - No multiprocessing overhead
    - No Redis coordination needed
    - Direct agent management
    - Built-in health monitoring
    """
    import logging
    from sqlmodel import Session, select
    from app.core.db import engine

    logger = logging.getLogger(__name__)
    global ROLE_CLASS_MAP
    
    # Lazy load role class map
    if ROLE_CLASS_MAP is None:
        ROLE_CLASS_MAP = get_role_class_map()

    logger.info("🚀 Initializing agent pool manager (optimized architecture)")
    await _initialize_pool(logger, ROLE_CLASS_MAP)


async def _initialize_pool(logger, role_class_map) -> None:
    """Initialize in-memory pool manager from DB."""
    from sqlmodel import Session, select
    from app.core.db import engine
    from app.services.pool_service import PoolService
    from app.models import AgentPool, PoolType

    pool_name = "universal_pool"

    # Skip if manager already exists
    if pool_name in _manager_registry:
        logger.info(f"Universal pool already exists, skipping")
        return

    try:
        # Get or create pool in DB
        with Session(engine) as db_session:
            pool_service = PoolService(db_session)
            db_pool = pool_service.get_pool_by_name(pool_name)
            
            if not db_pool:
                logger.info(f"Creating default pool '{pool_name}' in database")
                db_pool = pool_service.create_pool(
                    pool_name=pool_name,
                    role_type=None,  # Universal pool
                    pool_type=PoolType.FREE,
                    max_agents=100,
                    health_check_interval=60,
                    auto_created=True,
                )
            else:
                logger.info(f"Found existing pool '{pool_name}' in database (id={db_pool.id})")

        # Create manager with pool_id from DB
        manager = AgentPoolManager(
            pool_name=pool_name,
            max_agents=db_pool.max_agents,
            health_check_interval=db_pool.health_check_interval,
            pool_id=db_pool.id,
        )

        # Start manager
        if await manager.start():
            _manager_registry[pool_name] = manager
            logger.info(f"✓ Created agent pool: {pool_name} (supports all role types)")

            # Restore agents from database
            await _restore_agents(logger, manager, role_class_map)

        else:
            logger.error(f"✗ Failed to start agent pool manager: {pool_name}")

    except Exception as e:
        logger.error(f"✗ Error creating agent pool '{pool_name}': {e}", exc_info=True)


async def _restore_agents(logger, manager, role_class_map) -> None:
    """Restore agents for manager."""
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

        logger.info(f"📊 Restored {len(db_agents)} agents in agent pool")


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
    Uses AgentPoolManager with in-memory management (no multiprocessing).
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

    # Extract max_agents and health_check_interval if provided
    max_agents = 100  # Default for in-memory pool (no process overhead)
    health_check_interval = 60  # Default
    
    if request.config:
        max_agents = request.config.max_agents
        health_check_interval = request.config.health_check_interval

    # Create pool manager (no multiprocessing)
    manager = AgentPoolManager(
        pool_name=request.pool_name,
        max_agents=max_agents,
        health_check_interval=health_check_interval,
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

    Uses AgentPoolManager for in-memory agent management.
    """
    # Ensure role class map is loaded
    role_class_map = ensure_role_class_map()
    
    # Validate role type
    if request.role_type not in role_class_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role_type. Must be one of: {list(role_class_map.keys())}"
        )

    # Get persona template for this role
    persona_service = PersonaService(session)
    agent_service = AgentService(session)

    # Get existing personas used in this project (for diversity)
    existing_agents = session.exec(
        select(Agent).where(
            Agent.project_id == request.project_id,
            Agent.role_type == request.role_type,
            Agent.persona_template_id != None
        )
    ).all()
    used_persona_ids = [a.persona_template_id for a in existing_agents if a.persona_template_id]

    # Get random persona (prefer unused ones)
    persona = persona_service.get_random_persona_for_role(
        role_type=request.role_type,
        exclude_ids=used_persona_ids
    )

    if not persona:
        # Try again without exclusions (allow duplicates if necessary)
        persona = persona_service.get_random_persona_for_role(
            role_type=request.role_type,
            exclude_ids=[]
        )

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No persona templates found for role '{request.role_type}'. Please seed persona templates first by running: python app/db/seed_personas_script.py"
        )

    # Create agent from template
    db_agent = agent_service.create_from_template(
        project_id=request.project_id,
        persona_template=persona
    )

    logger.info(
        f"✓ Spawned {db_agent.human_name} ({request.role_type}) "
        f"with persona: {persona.communication_style}, traits: {', '.join(persona.personality_traits[:2]) if persona.personality_traits else 'default'}"
    )

    # Get universal pool manager
    pool_name = "universal_pool"
    manager = get_manager(pool_name)

    # Get role_class for this agent
    role_class = role_class_map[request.role_type]

    # Spawn via manager
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

    Uses AgentPoolManager for agent termination.
    """
    manager = get_manager(request.pool_name)

    # Terminate via manager
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
    from datetime import datetime, timezone

    # Aggregate stats from all pool managers
    total_agents = 0
    pools_list = []

    for pool_name, manager in _manager_registry.items():
        stats = await manager.get_stats()
        total_agents += stats.get("total_agents", 0)
        
        # Build PoolResponse for each pool
        pools_list.append(PoolResponse(
            pool_name=stats.get("pool_name", pool_name),
            role_type=stats.get("role_type", "universal"),
            active_agents=stats.get("active_agents", 0),
            max_agents=stats.get("max_agents", 0),
            total_spawned=stats.get("total_spawned", 0),
            total_terminated=stats.get("total_terminated", 0),
            is_running=stats.get("is_running", False),
            agents=stats.get("agents", []),
        ))

    # Calculate uptime from first manager
    uptime_seconds = 0.0
    if _manager_registry:
        first_manager = next(iter(_manager_registry.values()))
        stats = await first_manager.get_stats()
        uptime_seconds = stats.get("manager_uptime_seconds", 0.0)

    return SystemStatsResponse(
        uptime_seconds=uptime_seconds,
        total_pools=len(_manager_registry),
        total_agents=total_agents,
        pools=pools_list,
    )


@router.get("/monitor/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get comprehensive dashboard data for monitoring agent pools."""
    from datetime import datetime, timezone

    # Get stats from all managers
    pools_data = {}
    for pool_name, manager in _manager_registry.items():
        pools_data[pool_name] = await manager.get_stats()

    return {
        "pools": pools_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "in-memory",  # In-memory architecture
    }


@router.get("/monitor/alerts")
async def get_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get recent monitoring alerts.

    Note: Alerts tracking not yet implemented.
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
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get health status of all agents across all pools.

    Returns agent states from database.
    """
    health_data = {}
    
    for pool_name in _manager_registry.keys():
        # Extract role type from pool name (format: "{role_type}_pool")
        role_type = pool_name.replace("_pool", "")
        
        # Query agents from database
        agents = session.exec(
            select(Agent).where(Agent.role_type == role_type)
        ).all()

        pool_health = []
        for agent in agents:
            pool_health.append({
                "agent_id": str(agent.id),
                "status": agent.status.value,
                "role_type": agent.role_type,
                "name": agent.name,
                "human_name": agent.human_name,
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
# Note: Monitoring is built into AgentPoolManager
# No separate start/stop needed (starts automatically with pool initialization)


# ===== Pool DB Management Endpoints =====

@router.get("/pools/{pool_name}/db", response_model=AgentPoolPublic)
async def get_pool_db_info(
    pool_name: str,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get pool database information.
    
    Returns the persistent pool record from database including configuration,
    counters, and metadata.
    """
    pool_service = PoolService(session)
    pool = pool_service.get_pool_by_name(pool_name)
    
    if not pool:
        raise HTTPException(
            status_code=404,
            detail=f"Pool '{pool_name}' not found in database"
        )
    
    return pool


@router.put("/pools/{pool_id}/config", response_model=AgentPoolPublic)
async def update_pool_config(
    pool_id: UUID,
    config: UpdatePoolConfigRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update pool configuration in database.
    
    Updates pool settings like max_agents, health_check_interval, model config,
    and allowed templates. If pool is active, also updates runtime manager.
    """
    pool_service = PoolService(session)
    
    # Update DB record
    updated_pool = pool_service.update_pool(
        pool_id=pool_id,
        updated_by=current_user.id,
        **config.model_dump(exclude_unset=True)
    )
    
    if not updated_pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    # If pool is active, update runtime manager
    manager = _manager_registry.get(updated_pool.pool_name)
    if manager:
        if config.max_agents is not None:
            manager.max_agents = config.max_agents
        if config.health_check_interval is not None:
            manager.health_check_interval = config.health_check_interval
        
        logger.info(
            f"Updated runtime manager for pool '{updated_pool.pool_name}' "
            f"(max_agents={manager.max_agents}, health_check={manager.health_check_interval})"
        )
    
    return updated_pool


@router.get("/pools/{pool_id}/metrics", response_model=List[AgentPoolMetricsPublic])
async def get_pool_metrics_history(
    pool_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, le=1000),
) -> Any:
    """Get pool metrics history from database.
    
    Returns time-series metrics including token usage, requests per model,
    agent counts, and execution statistics.
    """
    from app.models import AgentPool
    
    pool_service = PoolService(session)
    
    # Verify pool exists
    pool = session.get(AgentPool, pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    metrics = pool_service.get_pool_metrics(
        pool_id=pool_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return metrics


@router.post("/pools/{pool_name}/scale")
async def scale_pool(
    pool_name: str,
    request: ScalePoolRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Scale pool to target agent count.
    
    Automatically spawns or terminates agents to reach target count.
    Spawns idle agents first if available in DB, terminates idle agents first when scaling down.
    """
    manager = get_manager(pool_name)
    current_count = len(manager.agents)
    target_agents = request.target_agents
    
    if target_agents == current_count:
        return {
            "message": "Pool already at target",
            "current_count": current_count,
            "target_count": target_agents
        }
    
    if target_agents > current_count:
        # Scale up - spawn more agents
        to_spawn = target_agents - current_count
        spawned = 0
        
        # Get idle agents from DB that can be spawned
        idle_agents = session.exec(
            select(Agent).where(
                Agent.pool_id == manager.pool_id,
                Agent.status == AgentStatus.stopped
            ).limit(to_spawn)
        ).all()
        
        # Get role class map
        role_class_map = ensure_role_class_map()
        
        for agent in idle_agents:
            role_class = role_class_map.get(agent.role_type)
            if not role_class:
                continue
            
            try:
                success = await manager.spawn_agent(
                    agent_id=agent.id,
                    role_class=role_class,
                    heartbeat_interval=30,
                    max_idle_time=300,
                )
                if success:
                    spawned += 1
            except Exception as e:
                logger.error(f"Error spawning agent {agent.id}: {e}")
        
        return {
            "message": f"Spawned {spawned} agents",
            "current_count": current_count + spawned,
            "target_count": target_agents,
            "spawned": spawned
        }
    
    else:
        # Scale down - terminate excess agents
        to_terminate = current_count - target_agents
        terminated = 0
        
        # Get idle agents first
        idle_agent_ids = [
            agent_id for agent_id, agent in manager.agents.items()
            if agent.state == AgentStatus.idle
        ]
        
        # Terminate idle agents first
        for agent_id in idle_agent_ids[:to_terminate]:
            try:
                success = await manager.terminate_agent(agent_id, graceful=True)
                if success:
                    terminated += 1
            except Exception as e:
                logger.error(f"Error terminating agent {agent_id}: {e}")
        
        # If still need to terminate more, terminate busy agents
        if terminated < to_terminate:
            remaining = to_terminate - terminated
            all_agent_ids = list(manager.agents.keys())
            
            for agent_id in all_agent_ids[:remaining]:
                if agent_id not in idle_agent_ids:  # Skip already terminated
                    try:
                        success = await manager.terminate_agent(agent_id, graceful=True)
                        if success:
                            terminated += 1
                    except Exception as e:
                        logger.error(f"Error terminating agent {agent_id}: {e}")
        
        return {
            "message": f"Terminated {terminated} agents",
            "current_count": current_count - terminated,
            "target_count": target_agents,
            "terminated": terminated
        }


@router.get("/pools/suggestions", response_model=List[PoolSuggestion])
async def get_pool_suggestions(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get pool creation suggestions based on current load.
    
    Analyzes current pool loads and suggests creating new pools when:
    - Existing pools are above 80% capacity
    - Specific role types need dedicated pools
    """
    from app.agents.core.pool_helpers import get_pool_load, should_create_new_pool
    
    suggestions = []
    
    for manager in _manager_registry.values():
        load = get_pool_load(manager)
        
        # Suggest overflow pool if above threshold
        if should_create_new_pool(manager, threshold=0.8):
            suggestions.append(PoolSuggestion(
                reason=f"Pool '{manager.pool_name}' is at {load*100:.0f}% capacity",
                recommended_pool_name=f"overflow_pool_{len(_manager_registry) + 1}",
                role_type=None,  # Universal
                estimated_agents=30
            ))
        
        # Suggest role-specific pools if load is high
        if load > 0.7 and manager.pool_name == "universal_pool":
            # Analyze which role types are most used
            role_counts: Dict[str, int] = {}
            for agent in manager.agents.values():
                role = getattr(agent, 'role_type', None)
                if role:
                    role_counts[role] = role_counts.get(role, 0) + 1
            
            # Suggest dedicated pool for roles with > 10 agents
            for role, count in role_counts.items():
                if count >= 10:
                    suggestions.append(PoolSuggestion(
                        reason=f"{count} {role} agents in universal pool - consider dedicated pool",
                        recommended_pool_name=f"{role}_pool",
                        role_type=role,
                        estimated_agents=count + 5
                    ))
    
    return suggestions


# ===== Server-Sent Events (SSE) for Real-time Updates =====

@router.get("/pools/events")
async def pool_events_stream(
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Server-Sent Events stream for real-time pool updates.
    
    Sends updates when:
    - Pool stats change (agent count, executions, etc.)
    - Agent health changes
    - Pool configuration updates
    - New alerts
    
    Event format:
    ```
    event: pool_stats
    data: {"pool_name": "universal_pool", "active_agents": 10, ...}
    
    event: agent_health
    data: {"agent_id": "...", "state": "idle", ...}
    ```
    """
    
    async def event_generator():
        """Generate SSE events."""
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'message': 'Connected to pool events stream'})}\n\n"
            
            while True:
                try:
                    # Collect all pool stats
                    pools_data = []
                    for pool_name, manager in _manager_registry.items():
                        try:
                            pool_stats = {
                                "pool_name": pool_name,
                                "active_agents": len(manager.agents),
                                "busy_agents": sum(1 for a in manager.agents.values() if a.state == AgentStatus.busy),
                                "idle_agents": sum(1 for a in manager.agents.values() if a.state == AgentStatus.idle),
                                "total_spawned": manager._total_spawned,
                                "total_terminated": manager._total_terminated,
                                "is_running": manager.is_running,
                            }
                            pools_data.append(pool_stats)
                        except Exception as e:
                            logger.error(f"Error collecting stats for pool '{pool_name}': {e}")
                    
                    # Send pool stats update
                    if pools_data:
                        yield f"event: pool_stats\ndata: {json.dumps(pools_data)}\n\n"
                    
                    # Collect all agent health
                    agents_health = []
                    for pool_name, manager in _manager_registry.items():
                        for agent_id, agent in manager.agents.items():
                            try:
                                health_data = {
                                    "agent_id": str(agent_id),
                                    "pool_name": pool_name,
                                    "state": agent.state.value if hasattr(agent.state, 'value') else str(agent.state),
                                    "healthy": True,  # Simplified - add real health check if needed
                                }
                                agents_health.append(health_data)
                            except Exception as e:
                                logger.error(f"Error collecting health for agent {agent_id}: {e}")
                    
                    # Send agent health update
                    if agents_health:
                        yield f"event: agent_health\ndata: {json.dumps(agents_health)}\n\n"
                    
                    # Send heartbeat to keep connection alive
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
                    
                    # Wait before next update
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
                except asyncio.CancelledError:
                    logger.info("SSE stream cancelled by client")
                    break
                except Exception as e:
                    logger.error(f"Error in SSE event generator: {e}")
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                    await asyncio.sleep(5)
                    
        except GeneratorExit:
            logger.info("SSE stream closed")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
