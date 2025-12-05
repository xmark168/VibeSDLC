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
import logging
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
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

# Global logger
logger = logging.getLogger(__name__)


# ===== System Status Management =====

class SystemStatus(str, Enum):
    """System-wide status for emergency controls."""
    RUNNING = "running"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    STOPPED = "stopped"


class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    status: SystemStatus
    paused_at: Optional[datetime] = None
    maintenance_message: Optional[str] = None
    active_pools: int = 0
    total_agents: int = 0
    accepting_tasks: bool = True


class EmergencyActionRequest(BaseModel):
    """Request model for emergency actions."""
    action: str  # pause, resume, stop, maintenance
    message: Optional[str] = None
    force: bool = False


# Global system state
_system_status: SystemStatus = SystemStatus.RUNNING
_status_changed_at: Optional[datetime] = None
_maintenance_message: Optional[str] = None

# Role class mapping - lazy loaded to avoid circular imports
def get_role_class_map():
    """Get role class mapping with lazy imports."""
    from app.agents.team_leader import TeamLeader
    from app.agents.developer_v2 import DeveloperV2
    from app.agents.tester import Tester
    from app.agents.business_analyst import BusinessAnalyst
    
    return {
        "team_leader": TeamLeader,
        "developer": DeveloperV2,
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
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """List all agent pool managers and their statistics."""
    from app.models import AgentPool
    from sqlalchemy import func
    
    stats_list = []
    
    # Get stats from in-memory managers
    for manager in _manager_registry.values():
        stats = await manager.get_stats()
        stats_list.append(PoolResponse(**stats))
    
    # Fallback: If no managers, create a virtual pool from DB agents
    if not stats_list:
        # Count agents by status
        total_agents = session.exec(select(func.count(Agent.id))).one() or 0
        idle_agents = session.exec(
            select(func.count(Agent.id))
            .where(Agent.status == AgentStatus.idle)
        ).one() or 0
        busy_agents = session.exec(
            select(func.count(Agent.id))
            .where(Agent.status == AgentStatus.busy)
        ).one() or 0
        active_agents = idle_agents + busy_agents
        
        # Get agent list
        agents = session.exec(select(Agent).limit(100)).all()
        agents_data = [
            {
                "agent_id": str(a.id),
                "role_type": a.role_type,
                "status": a.status.value,
                "human_name": a.human_name,
            }
            for a in agents
        ]
        
        # Get execution stats
        total_exec = session.exec(select(func.count(AgentExecution.id))).one() or 0
        success_exec = session.exec(
            select(func.count(AgentExecution.id))
            .where(AgentExecution.status == AgentExecutionStatus.COMPLETED)
        ).one() or 0
        failed_exec = session.exec(
            select(func.count(AgentExecution.id))
            .where(AgentExecution.status == AgentExecutionStatus.FAILED)
        ).one() or 0
        success_rate = (success_exec / total_exec) if total_exec > 0 else 0.0
        load = (busy_agents / total_agents * 100) if total_agents > 0 else 0.0
        
        stats_list.append(PoolResponse(
            pool_name="universal_pool",
            role_type="universal",
            total_agents=total_agents,
            active_agents=active_agents,
            busy_agents=busy_agents,
            idle_agents=idle_agents,
            max_agents=100,
            is_running=True,
            total_spawned=total_agents,
            total_terminated=0,
            total_executions=total_exec,
            successful_executions=success_exec,
            failed_executions=failed_exec,
            success_rate=success_rate,
            load=load,
            agents=agents_data,
        ))
    
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
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get system-wide agent statistics from all pool managers."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func

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

    # Query execution stats from database (real-time)
    total_executions = session.exec(
        select(func.count(AgentExecution.id))
    ).one() or 0
    
    successful_executions = session.exec(
        select(func.count(AgentExecution.id))
        .where(AgentExecution.status == AgentExecutionStatus.COMPLETED)
    ).one() or 0
    
    failed_executions = session.exec(
        select(func.count(AgentExecution.id))
        .where(AgentExecution.status == AgentExecutionStatus.FAILED)
    ).one() or 0
    
    success_rate = (successful_executions / total_executions) if total_executions > 0 else 0.0
    
    # Count recent alerts (last 24h) - using executions with errors as proxy
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_alerts = session.exec(
        select(func.count(AgentExecution.id))
        .where(
            AgentExecution.status == AgentExecutionStatus.FAILED,
            AgentExecution.created_at >= yesterday
        )
    ).one() or 0

    return SystemStatsResponse(
        uptime_seconds=uptime_seconds,
        total_pools=len(_manager_registry),
        total_agents=total_agents,
        total_executions=total_executions,
        successful_executions=successful_executions,
        failed_executions=failed_executions,
        success_rate=success_rate,
        recent_alerts=recent_alerts,
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

    # Query token usage from AgentExecution table (real data)
    query = select(
        AgentExecution.agent_type,
        func.sum(AgentExecution.token_used).label("total_tokens"),
        func.sum(AgentExecution.llm_calls).label("total_llm_calls"),
        func.avg(AgentExecution.duration_ms).label("avg_duration_ms"),
        func.count(AgentExecution.id).label("execution_count"),
    ).where(
        AgentExecution.created_at >= cutoff_time
    ).group_by(
        AgentExecution.agent_type
    )

    results = session.exec(query).all()

    token_data = []
    total_tokens = 0
    total_llm_calls = 0

    for row in results:
        tokens = row.total_tokens or 0
        llm_calls = row.total_llm_calls or 0

        # Rough cost estimate (using GPT-4 pricing as example: $0.03/1K tokens)
        estimated_cost = (tokens / 1000) * 0.03

        token_data.append({
            "agent_type": row.agent_type,
            "total_tokens": tokens,
            "total_llm_calls": llm_calls,
            "avg_tokens_per_call": round(tokens / llm_calls, 2) if llm_calls > 0 else 0,
            "avg_duration_ms": round(row.avg_duration_ms or 0, 2),
            "execution_count": row.execution_count,
            "estimated_cost_usd": round(estimated_cost, 4),
        })

        total_tokens += tokens
        total_llm_calls += llm_calls

    # Also get timeseries data for charts
    timeseries_query = select(
        AgentExecution.created_at,
        AgentExecution.token_used,
        AgentExecution.llm_calls,
    ).where(
        AgentExecution.created_at >= cutoff_time
    ).order_by(AgentExecution.created_at.asc())

    timeseries_results = session.exec(timeseries_query).all()
    
    timeseries_data = [
        {
            "timestamp": r.created_at.isoformat() if r.created_at else None,
            "total_tokens": r.token_used or 0,
            "llm_calls": r.llm_calls or 0,
        }
        for r in timeseries_results
    ]

    return {
        "time_range": time_range,
        "group_by": group_by,
        "summary": {
            "total_tokens": total_tokens,
            "total_llm_calls": total_llm_calls,
            "avg_tokens_per_call": round(total_tokens / total_llm_calls, 2) if total_llm_calls > 0 else 0,
            "estimated_total_cost_usd": round((total_tokens / 1000) * 0.03, 4),
        },
        "data": timeseries_data,
        "by_agent_type": token_data,
        "count": len(timeseries_data),
    }


@router.get("/health")
async def get_all_agent_health(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get health status of all agents across all pools.

    Returns agent states combining in-memory managers and database.
    """
    from datetime import datetime, timezone
    from sqlalchemy import func
    
    health_data = {}
    
    # If we have pools in registry, get real-time data from managers
    if _manager_registry:
        for pool_name, manager in _manager_registry.items():
            pool_health = []
            
            # Get agents from manager (in-memory state)
            for agent_id, agent_instance in manager.agents.items():
                # Get agent info from database for additional details
                db_agent = session.get(Agent, agent_id)
                
                # Query execution stats for this agent
                exec_count = session.exec(
                    select(func.count(AgentExecution.id))
                    .where(AgentExecution.agent_name == (db_agent.human_name if db_agent else str(agent_id)))
                ).one() or 0
                
                success_count = session.exec(
                    select(func.count(AgentExecution.id))
                    .where(
                        AgentExecution.agent_name == (db_agent.human_name if db_agent else str(agent_id)),
                        AgentExecution.status == AgentExecutionStatus.COMPLETED
                    )
                ).one() or 0
                
                # Calculate uptime
                uptime = 0.0
                if hasattr(agent_instance, 'started_at') and agent_instance.started_at:
                    uptime = (datetime.now(timezone.utc) - agent_instance.started_at).total_seconds()
                
                pool_health.append({
                    "agent_id": str(agent_id),
                    "role_name": db_agent.role_type if db_agent else getattr(agent_instance, 'role_type', 'unknown'),
                    "state": getattr(agent_instance, 'state', AgentStatus.idle).value if hasattr(getattr(agent_instance, 'state', None), 'value') else str(getattr(agent_instance, 'state', 'idle')),
                    "healthy": True,  # In-memory agent is healthy
                    "uptime_seconds": uptime,
                    "total_executions": exec_count,
                    "success_rate": (success_count / exec_count) if exec_count > 0 else 0.0,
                    "idle_seconds": 0,  # Could be calculated if tracking
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                })
            
            health_data[pool_name] = pool_health
    
    # Fallback: If registry is empty, query ALL agents from database
    if not health_data:
        all_agents = session.exec(select(Agent)).all()
        
        pool_health = []
        for agent in all_agents:
            # Query execution stats
            exec_count = session.exec(
                select(func.count(AgentExecution.id))
                .where(AgentExecution.agent_name == agent.human_name)
            ).one() or 0
            
            success_count = session.exec(
                select(func.count(AgentExecution.id))
                .where(
                    AgentExecution.agent_name == agent.human_name,
                    AgentExecution.status == AgentExecutionStatus.COMPLETED
                )
            ).one() or 0
            
            pool_health.append({
                "agent_id": str(agent.id),
                "role_name": agent.role_type,
                "state": agent.status.value,
                "healthy": agent.status not in [AgentStatus.error, AgentStatus.terminated],
                "uptime_seconds": 0,
                "total_executions": exec_count,
                "success_rate": (success_count / exec_count) if exec_count > 0 else 0.0,
                "idle_seconds": 0,
                "last_heartbeat": agent.updated_at.isoformat() if agent.updated_at else None,
            })
        
        health_data["universal_pool"] = pool_health

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


# ===== Emergency Control Endpoints =====

@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get current system status including emergency state.
    
    Returns system-wide status, pool counts, and whether tasks are being accepted.
    """
    global _system_status, _status_changed_at, _maintenance_message
    
    total_agents = 0
    for manager in _manager_registry.values():
        total_agents += len(manager.agents)
    
    accepting_tasks = _system_status == SystemStatus.RUNNING
    
    return SystemStatusResponse(
        status=_system_status,
        paused_at=_status_changed_at if _system_status != SystemStatus.RUNNING else None,
        maintenance_message=_maintenance_message,
        active_pools=len(_manager_registry),
        total_agents=total_agents,
        accepting_tasks=accepting_tasks,
    )


@router.post("/system/emergency/pause")
async def emergency_pause_all(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Emergency PAUSE: Stop all agents from accepting new tasks.
    
    Agents will finish current tasks but won't accept new ones.
    Use this when you need to temporarily halt processing without losing work.
    """
    global _system_status, _status_changed_at
    
    if _system_status == SystemStatus.PAUSED:
        return {"message": "System already paused", "status": _system_status.value}
    
    _system_status = SystemStatus.PAUSED
    _status_changed_at = datetime.now()
    
    # Notify all agents to stop accepting tasks
    paused_count = 0
    for pool_name, manager in _manager_registry.items():
        for agent_id, agent in manager.agents.items():
            try:
                # Set agent to not accept new tasks (implementation depends on agent)
                if hasattr(agent, 'pause'):
                    await agent.pause()
                paused_count += 1
            except Exception as e:
                logger.error(f"Error pausing agent {agent_id}: {e}")
    
    logger.warning(f"EMERGENCY PAUSE: {paused_count} agents paused by {current_user.email}")
    
    return {
        "message": f"System paused. {paused_count} agents stopped accepting tasks.",
        "status": _system_status.value,
        "paused_at": _status_changed_at.isoformat(),
        "agents_affected": paused_count,
    }


@router.post("/system/emergency/resume")
async def emergency_resume_all(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Resume all agents after pause or maintenance.
    
    Agents will start accepting new tasks again.
    """
    global _system_status, _status_changed_at, _maintenance_message
    
    if _system_status == SystemStatus.RUNNING:
        return {"message": "System already running", "status": _system_status.value}
    
    if _system_status == SystemStatus.STOPPED:
        raise HTTPException(
            status_code=400,
            detail="Cannot resume stopped system. Use /system/start to restart."
        )
    
    previous_status = _system_status
    _system_status = SystemStatus.RUNNING
    _status_changed_at = datetime.now()
    _maintenance_message = None
    
    # Resume all agents
    resumed_count = 0
    for pool_name, manager in _manager_registry.items():
        for agent_id, agent in manager.agents.items():
            try:
                if hasattr(agent, 'resume'):
                    await agent.resume()
                resumed_count += 1
            except Exception as e:
                logger.error(f"Error resuming agent {agent_id}: {e}")
    
    logger.info(f"System resumed from {previous_status.value} by {current_user.email}. {resumed_count} agents active.")
    
    return {
        "message": f"System resumed. {resumed_count} agents now accepting tasks.",
        "status": _system_status.value,
        "previous_status": previous_status.value,
        "agents_affected": resumed_count,
    }


@router.post("/system/emergency/stop")
async def emergency_stop_all(
    force: bool = Query(default=False, description="Force stop without waiting for tasks"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Emergency STOP: Terminate all agents immediately.
    
    WARNING: This will terminate all running agents. Use with caution.
    - force=False: Wait for current tasks to complete (graceful)
    - force=True: Stop immediately without waiting (may lose work)
    """
    global _system_status, _status_changed_at
    
    _system_status = SystemStatus.STOPPED
    _status_changed_at = datetime.now()
    
    stopped_count = 0
    failed_count = 0
    
    for pool_name, manager in list(_manager_registry.items()):
        agent_ids = list(manager.agents.keys())
        for agent_id in agent_ids:
            try:
                success = await manager.terminate_agent(agent_id, graceful=not force)
                if success:
                    stopped_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error stopping agent {agent_id}: {e}")
                failed_count += 1
    
    logger.critical(
        f"EMERGENCY STOP: {stopped_count} agents terminated, {failed_count} failed. "
        f"Initiated by {current_user.email}"
    )
    
    return {
        "message": f"Emergency stop executed. {stopped_count} agents terminated.",
        "status": _system_status.value,
        "stopped_at": _status_changed_at.isoformat(),
        "agents_stopped": stopped_count,
        "agents_failed": failed_count,
        "force": force,
    }


@router.post("/system/emergency/maintenance")
async def enter_maintenance_mode(
    message: str = Query(default="System under maintenance", description="Maintenance message"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Enter maintenance mode.
    
    Similar to pause but with a custom message for users.
    Useful for planned maintenance windows.
    """
    global _system_status, _status_changed_at, _maintenance_message
    
    _system_status = SystemStatus.MAINTENANCE
    _status_changed_at = datetime.now()
    _maintenance_message = message
    
    # Pause all agents
    paused_count = 0
    for pool_name, manager in _manager_registry.items():
        for agent_id, agent in manager.agents.items():
            try:
                if hasattr(agent, 'pause'):
                    await agent.pause()
                paused_count += 1
            except Exception as e:
                logger.error(f"Error pausing agent {agent_id}: {e}")
    
    logger.warning(
        f"MAINTENANCE MODE: Entered by {current_user.email}. "
        f"Message: {message}. {paused_count} agents paused."
    )
    
    return {
        "message": f"Maintenance mode active. {paused_count} agents paused.",
        "status": _system_status.value,
        "maintenance_message": _maintenance_message,
        "started_at": _status_changed_at.isoformat(),
        "agents_affected": paused_count,
    }


@router.post("/system/emergency/restart-pool/{pool_name}")
async def restart_pool(
    pool_name: str,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Restart all agents in a specific pool.
    
    Useful when a pool is experiencing issues.
    """
    manager = get_manager(pool_name)
    
    # Get all agent IDs and role classes before terminating
    agents_info = []
    role_class_map = ensure_role_class_map()
    
    for agent_id, agent in list(manager.agents.items()):
        role_type = getattr(agent, 'role_type', None)
        if role_type and role_type in role_class_map:
            agents_info.append({
                'agent_id': agent_id,
                'role_class': role_class_map[role_type],
            })
    
    # Terminate all agents
    terminated = 0
    for info in agents_info:
        try:
            await manager.terminate_agent(info['agent_id'], graceful=True)
            terminated += 1
        except Exception as e:
            logger.error(f"Error terminating agent {info['agent_id']}: {e}")
    
    # Small delay for cleanup
    await asyncio.sleep(1)
    
    # Respawn agents
    respawned = 0
    for info in agents_info:
        try:
            success = await manager.spawn_agent(
                agent_id=info['agent_id'],
                role_class=info['role_class'],
                heartbeat_interval=30,
                max_idle_time=300,
            )
            if success:
                respawned += 1
        except Exception as e:
            logger.error(f"Error respawning agent {info['agent_id']}: {e}")
    
    logger.info(
        f"Pool '{pool_name}' restarted by {current_user.email}. "
        f"Terminated: {terminated}, Respawned: {respawned}"
    )
    
    return {
        "message": f"Pool '{pool_name}' restarted.",
        "pool_name": pool_name,
        "agents_terminated": terminated,
        "agents_respawned": respawned,
    }


# Helper function to check if system is accepting tasks
def is_system_accepting_tasks() -> bool:
    """Check if system is currently accepting new tasks."""
    return _system_status == SystemStatus.RUNNING


def get_system_status() -> SystemStatus:
    """Get current system status."""
    return _system_status


# ===== Agent Configuration Endpoints =====

class AgentConfigSchema(BaseModel):
    """Schema for agent configuration."""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    model_name: Optional[str] = None
    system_prompt_override: Optional[str] = None
    tool_permissions: Optional[List[str]] = None
    timeout_seconds: int = 300
    retry_count: int = 3


class AgentConfigResponse(BaseModel):
    """Response model for agent configuration."""
    agent_id: str
    agent_name: str
    role_type: str
    config: AgentConfigSchema
    updated_at: Optional[datetime] = None


@router.get("/config/{agent_id}", response_model=AgentConfigResponse)
async def get_agent_config(
    agent_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get agent configuration.
    
    Returns the agent's LLM configuration settings including model parameters,
    system prompts, and tool permissions.
    """
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    # Extract config from persona_metadata
    metadata = agent.persona_metadata or {}
    llm_config = metadata.get("llm_config", {})
    
    config = AgentConfigSchema(
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 4096),
        top_p=llm_config.get("top_p", 1.0),
        model_name=llm_config.get("model_name"),
        system_prompt_override=llm_config.get("system_prompt_override"),
        tool_permissions=llm_config.get("tool_permissions"),
        timeout_seconds=llm_config.get("timeout_seconds", 300),
        retry_count=llm_config.get("retry_count", 3),
    )
    
    return AgentConfigResponse(
        agent_id=str(agent.id),
        agent_name=agent.human_name,
        role_type=agent.role_type,
        config=config,
        updated_at=agent.updated_at,
    )


@router.put("/config/{agent_id}", response_model=AgentConfigResponse)
async def update_agent_config(
    agent_id: UUID,
    config: AgentConfigSchema,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update agent configuration.
    
    Updates the agent's LLM configuration settings. Changes take effect
    immediately for the running agent.
    """
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    # Update persona_metadata with new config
    metadata = agent.persona_metadata or {}
    metadata["llm_config"] = {
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "top_p": config.top_p,
        "model_name": config.model_name,
        "system_prompt_override": config.system_prompt_override,
        "tool_permissions": config.tool_permissions,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
    }
    
    agent.persona_metadata = metadata
    session.add(agent)
    session.commit()
    session.refresh(agent)
    
    # If agent is running, try to update its config in memory
    for manager in _manager_registry.values():
        running_agent = manager.agents.get(agent_id)
        if running_agent:
            try:
                # Update agent's config if it supports it
                if hasattr(running_agent, 'update_config'):
                    running_agent.update_config(metadata["llm_config"])
                logger.info(f"Updated running agent {agent_id} config")
            except Exception as e:
                logger.warning(f"Could not update running agent config: {e}")
            break
    
    logger.info(f"Agent {agent_id} config updated by {current_user.email}")
    
    return AgentConfigResponse(
        agent_id=str(agent.id),
        agent_name=agent.human_name,
        role_type=agent.role_type,
        config=config,
        updated_at=agent.updated_at,
    )


@router.get("/config/defaults/{role_type}")
async def get_default_config(
    role_type: str,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get default configuration for a role type.
    
    Returns recommended default settings for the specified agent role.
    """
    # Default configs per role type
    defaults = {
        "team_leader": {
            "temperature": 0.7,
            "max_tokens": 4096,
            "top_p": 1.0,
            "timeout_seconds": 300,
            "retry_count": 3,
            "description": "Balanced settings for coordination and routing tasks",
        },
        "developer": {
            "temperature": 0.3,
            "max_tokens": 8192,
            "top_p": 0.95,
            "timeout_seconds": 600,
            "retry_count": 2,
            "description": "Lower temperature for more deterministic code generation",
        },
        "business_analyst": {
            "temperature": 0.6,
            "max_tokens": 6144,
            "top_p": 1.0,
            "timeout_seconds": 400,
            "retry_count": 3,
            "description": "Moderate settings for requirements analysis and documentation",
        },
        "tester": {
            "temperature": 0.4,
            "max_tokens": 4096,
            "top_p": 0.9,
            "timeout_seconds": 500,
            "retry_count": 2,
            "description": "Lower temperature for consistent test generation",
        },
    }
    
    if role_type not in defaults:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role type: {role_type}. Valid types: {list(defaults.keys())}"
        )
    
    return {
        "role_type": role_type,
        "defaults": defaults[role_type],
    }


@router.post("/config/{agent_id}/reset")
async def reset_agent_config(
    agent_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Reset agent configuration to defaults.
    
    Removes custom configuration and reverts to role-type defaults.
    """
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    # Remove llm_config from metadata
    metadata = agent.persona_metadata or {}
    if "llm_config" in metadata:
        del metadata["llm_config"]
    
    agent.persona_metadata = metadata
    session.add(agent)
    session.commit()
    
    logger.info(f"Agent {agent_id} config reset to defaults by {current_user.email}")
    
    return {
        "message": f"Agent configuration reset to defaults",
        "agent_id": str(agent_id),
        "role_type": agent.role_type,
    }


# ===== Bulk Operations Endpoints =====

class BulkAgentRequest(BaseModel):
    """Request model for bulk agent operations."""
    agent_ids: List[str]
    pool_name: Optional[str] = None


class BulkSpawnRequest(BaseModel):
    """Request model for bulk spawn operation."""
    role_type: str
    count: int
    project_id: str
    pool_name: str = "universal_pool"


class BulkOperationResponse(BaseModel):
    """Response model for bulk operations."""
    success_count: int
    failed_count: int
    total_requested: int
    results: List[Dict[str, Any]]
    message: str


@router.post("/bulk/terminate", response_model=BulkOperationResponse)
async def bulk_terminate_agents(
    request: BulkAgentRequest,
    session: SessionDep,
    graceful: bool = Query(default=True, description="Wait for tasks to complete"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Terminate multiple agents at once.
    
    Useful for scaling down or clearing unhealthy agents.
    """
    results = []
    success_count = 0
    failed_count = 0
    
    for agent_id_str in request.agent_ids:
        try:
            agent_id = UUID(agent_id_str)
            
            # Find which pool this agent is in
            terminated = False
            for pool_name, manager in _manager_registry.items():
                if agent_id in manager.agents:
                    success = await manager.terminate_agent(agent_id, graceful=graceful)
                    if success:
                        success_count += 1
                        results.append({
                            "agent_id": agent_id_str,
                            "status": "terminated",
                            "pool": pool_name,
                        })
                        terminated = True
                    else:
                        failed_count += 1
                        results.append({
                            "agent_id": agent_id_str,
                            "status": "failed",
                            "error": "Termination failed",
                        })
                        terminated = True
                    break
            
            if not terminated:
                failed_count += 1
                results.append({
                    "agent_id": agent_id_str,
                    "status": "not_found",
                    "error": "Agent not found in any pool",
                })
                
        except Exception as e:
            failed_count += 1
            results.append({
                "agent_id": agent_id_str,
                "status": "error",
                "error": str(e),
            })
    
    logger.info(
        f"Bulk terminate by {current_user.email}: "
        f"{success_count} terminated, {failed_count} failed"
    )
    
    return BulkOperationResponse(
        success_count=success_count,
        failed_count=failed_count,
        total_requested=len(request.agent_ids),
        results=results,
        message=f"Terminated {success_count} of {len(request.agent_ids)} agents",
    )


@router.post("/bulk/set-idle", response_model=BulkOperationResponse)
async def bulk_set_idle(
    request: BulkAgentRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Set multiple agents to idle state.
    
    Forces agents to stop current work and become available.
    """
    results = []
    success_count = 0
    failed_count = 0
    
    for agent_id_str in request.agent_ids:
        try:
            agent_id = UUID(agent_id_str)
            
            # Find agent and set idle
            found = False
            for pool_name, manager in _manager_registry.items():
                agent = manager.agents.get(agent_id)
                if agent:
                    found = True
                    previous_state = agent.state
                    
                    # Update agent state
                    if hasattr(agent, 'set_idle'):
                        await agent.set_idle()
                    agent.state = AgentStatus.idle
                    
                    # Update in database
                    db_agent = session.get(Agent, agent_id)
                    if db_agent:
                        db_agent.status = AgentStatus.idle
                        session.add(db_agent)
                    
                    success_count += 1
                    results.append({
                        "agent_id": agent_id_str,
                        "status": "idle",
                        "previous_state": previous_state.value if hasattr(previous_state, 'value') else str(previous_state),
                    })
                    break
            
            if not found:
                failed_count += 1
                results.append({
                    "agent_id": agent_id_str,
                    "status": "not_found",
                    "error": "Agent not found",
                })
                
        except Exception as e:
            failed_count += 1
            results.append({
                "agent_id": agent_id_str,
                "status": "error",
                "error": str(e),
            })
    
    session.commit()
    
    logger.info(
        f"Bulk set-idle by {current_user.email}: "
        f"{success_count} set idle, {failed_count} failed"
    )
    
    return BulkOperationResponse(
        success_count=success_count,
        failed_count=failed_count,
        total_requested=len(request.agent_ids),
        results=results,
        message=f"Set {success_count} of {len(request.agent_ids)} agents to idle",
    )


@router.post("/bulk/restart", response_model=BulkOperationResponse)
async def bulk_restart_agents(
    request: BulkAgentRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Restart multiple agents.
    
    Terminates and respawns each agent, useful for applying config changes
    or recovering from errors.
    """
    results = []
    success_count = 0
    failed_count = 0
    role_class_map = ensure_role_class_map()
    
    for agent_id_str in request.agent_ids:
        try:
            agent_id = UUID(agent_id_str)
            
            # Get agent info from database
            db_agent = session.get(Agent, agent_id)
            if not db_agent:
                failed_count += 1
                results.append({
                    "agent_id": agent_id_str,
                    "status": "not_found",
                    "error": "Agent not found in database",
                })
                continue
            
            role_class = role_class_map.get(db_agent.role_type)
            if not role_class:
                failed_count += 1
                results.append({
                    "agent_id": agent_id_str,
                    "status": "error",
                    "error": f"Unknown role type: {db_agent.role_type}",
                })
                continue
            
            # Find and terminate agent
            terminated = False
            target_manager = None
            for pool_name, manager in _manager_registry.items():
                if agent_id in manager.agents:
                    await manager.terminate_agent(agent_id, graceful=True)
                    terminated = True
                    target_manager = manager
                    break
            
            if not target_manager:
                # Use universal pool if agent wasn't running
                target_manager = _manager_registry.get("universal_pool")
            
            if not target_manager:
                failed_count += 1
                results.append({
                    "agent_id": agent_id_str,
                    "status": "error",
                    "error": "No pool available",
                })
                continue
            
            # Small delay before respawn
            await asyncio.sleep(0.5)
            
            # Respawn agent
            success = await target_manager.spawn_agent(
                agent_id=agent_id,
                role_class=role_class,
                heartbeat_interval=30,
                max_idle_time=300,
            )
            
            if success:
                success_count += 1
                results.append({
                    "agent_id": agent_id_str,
                    "status": "restarted",
                    "pool": target_manager.pool_name,
                })
            else:
                failed_count += 1
                results.append({
                    "agent_id": agent_id_str,
                    "status": "spawn_failed",
                    "error": "Failed to respawn agent",
                })
                
        except Exception as e:
            failed_count += 1
            results.append({
                "agent_id": agent_id_str,
                "status": "error",
                "error": str(e),
            })
    
    logger.info(
        f"Bulk restart by {current_user.email}: "
        f"{success_count} restarted, {failed_count} failed"
    )
    
    return BulkOperationResponse(
        success_count=success_count,
        failed_count=failed_count,
        total_requested=len(request.agent_ids),
        results=results,
        message=f"Restarted {success_count} of {len(request.agent_ids)} agents",
    )


@router.post("/bulk/spawn", response_model=BulkOperationResponse)
async def bulk_spawn_agents(
    request: BulkSpawnRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Spawn multiple agents of a specific role type.
    
    Useful for quickly scaling up capacity.
    """
    role_class_map = ensure_role_class_map()
    
    if request.role_type not in role_class_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role_type. Must be one of: {list(role_class_map.keys())}"
        )
    
    if request.count < 1 or request.count > 20:
        raise HTTPException(
            status_code=400,
            detail="Count must be between 1 and 20"
        )
    
    manager = _manager_registry.get(request.pool_name)
    if not manager:
        raise HTTPException(
            status_code=404,
            detail=f"Pool '{request.pool_name}' not found"
        )
    
    # Check capacity
    available_slots = manager.max_agents - len(manager.agents)
    if available_slots < request.count:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough capacity. Available: {available_slots}, Requested: {request.count}"
        )
    
    results = []
    success_count = 0
    failed_count = 0
    role_class = role_class_map[request.role_type]
    project_id = UUID(request.project_id)
    
    # Get persona service for diverse personas
    from app.services.persona_service import PersonaService
    from app.services.agent_service import AgentService
    
    persona_service = PersonaService(session)
    agent_service = AgentService(session)
    
    # Get used persona IDs for diversity
    existing_agents = session.exec(
        select(Agent).where(
            Agent.project_id == project_id,
            Agent.role_type == request.role_type,
            Agent.persona_template_id != None
        )
    ).all()
    used_persona_ids = [a.persona_template_id for a in existing_agents if a.persona_template_id]
    
    for i in range(request.count):
        try:
            # Get persona template
            persona = persona_service.get_random_persona_for_role(
                role_type=request.role_type,
                exclude_ids=used_persona_ids
            )
            
            if not persona:
                persona = persona_service.get_random_persona_for_role(
                    role_type=request.role_type,
                    exclude_ids=[]
                )
            
            if not persona:
                failed_count += 1
                results.append({
                    "index": i,
                    "status": "error",
                    "error": f"No persona template found for {request.role_type}",
                })
                continue
            
            # Create agent from template
            db_agent = agent_service.create_from_template(
                project_id=project_id,
                persona_template=persona
            )
            
            # Track used persona
            if persona.id not in used_persona_ids:
                used_persona_ids.append(persona.id)
            
            # Spawn agent
            success = await manager.spawn_agent(
                agent_id=db_agent.id,
                role_class=role_class,
                heartbeat_interval=30,
                max_idle_time=300,
            )
            
            if success:
                success_count += 1
                results.append({
                    "index": i,
                    "agent_id": str(db_agent.id),
                    "agent_name": db_agent.human_name,
                    "status": "spawned",
                })
            else:
                # Rollback DB entry
                session.delete(db_agent)
                failed_count += 1
                results.append({
                    "index": i,
                    "status": "spawn_failed",
                    "error": "Failed to spawn agent",
                })
                
        except Exception as e:
            failed_count += 1
            results.append({
                "index": i,
                "status": "error",
                "error": str(e),
            })
    
    session.commit()
    
    logger.info(
        f"Bulk spawn by {current_user.email}: "
        f"{success_count} {request.role_type} agents spawned, {failed_count} failed"
    )
    
    return BulkOperationResponse(
        success_count=success_count,
        failed_count=failed_count,
        total_requested=request.count,
        results=results,
        message=f"Spawned {success_count} of {request.count} {request.role_type} agents",
    )


# ===== Phase 3: Auto-scaling Rules =====

class ScalingTriggerType(str, Enum):
    """Types of scaling triggers."""
    SCHEDULE = "schedule"      # Time-based scaling
    LOAD = "load"              # Load-based scaling
    QUEUE_DEPTH = "queue_depth" # Task queue depth


class ScalingAction(str, Enum):
    """Scaling actions."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SET_COUNT = "set_count"


class AutoScalingRule(BaseModel):
    """Auto-scaling rule configuration."""
    id: Optional[str] = None
    name: str
    pool_name: str
    enabled: bool = True
    trigger_type: ScalingTriggerType
    # Schedule trigger config
    cron_expression: Optional[str] = None  # e.g., "0 9 * * 1-5" (9 AM weekdays)
    timezone: Optional[str] = "UTC"
    # Load trigger config
    metric: Optional[str] = None  # cpu_percent, memory_percent, active_ratio
    threshold_high: Optional[float] = None  # Scale up when above
    threshold_low: Optional[float] = None   # Scale down when below
    cooldown_seconds: int = 300  # Min time between scaling actions
    # Action config
    action: ScalingAction
    target_count: Optional[int] = None  # For SET_COUNT
    scale_amount: int = 1  # For SCALE_UP/DOWN
    min_agents: int = 1
    max_agents: int = 10
    # Role filter
    role_type: Optional[str] = None  # Only scale specific role
    created_at: Optional[datetime] = None
    last_triggered: Optional[datetime] = None


class AutoScalingRuleCreate(BaseModel):
    """Request to create auto-scaling rule."""
    name: str
    pool_name: str
    enabled: bool = True
    trigger_type: ScalingTriggerType
    cron_expression: Optional[str] = None
    timezone: Optional[str] = "UTC"
    metric: Optional[str] = None
    threshold_high: Optional[float] = None
    threshold_low: Optional[float] = None
    cooldown_seconds: int = 300
    action: ScalingAction
    target_count: Optional[int] = None
    scale_amount: int = 1
    min_agents: int = 1
    max_agents: int = 10
    role_type: Optional[str] = None


# In-memory storage for auto-scaling rules (in production, use database)
_auto_scaling_rules: Dict[str, AutoScalingRule] = {}
_rule_id_counter = 0


@router.get("/scaling/rules")
async def list_auto_scaling_rules(
    pool_name: Optional[str] = None,
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user),
) -> List[AutoScalingRule]:
    """List all auto-scaling rules."""
    rules = list(_auto_scaling_rules.values())
    
    if pool_name:
        rules = [r for r in rules if r.pool_name == pool_name]
    
    if enabled_only:
        rules = [r for r in rules if r.enabled]
    
    return rules


@router.post("/scaling/rules")
async def create_auto_scaling_rule(
    request: AutoScalingRuleCreate,
    current_user: User = Depends(get_current_user),
) -> AutoScalingRule:
    """Create a new auto-scaling rule."""
    global _rule_id_counter
    
    # Validate pool exists
    if request.pool_name not in _manager_registry:
        raise HTTPException(
            status_code=404,
            detail=f"Pool '{request.pool_name}' not found"
        )
    
    # Validate trigger config
    if request.trigger_type == ScalingTriggerType.SCHEDULE:
        if not request.cron_expression:
            raise HTTPException(
                status_code=400,
                detail="cron_expression required for schedule trigger"
            )
    elif request.trigger_type in (ScalingTriggerType.LOAD, ScalingTriggerType.QUEUE_DEPTH):
        if request.threshold_high is None and request.threshold_low is None:
            raise HTTPException(
                status_code=400,
                detail="threshold_high or threshold_low required for load/queue triggers"
            )
    
    # Validate action config
    if request.action == ScalingAction.SET_COUNT and request.target_count is None:
        raise HTTPException(
            status_code=400,
            detail="target_count required for SET_COUNT action"
        )
    
    _rule_id_counter += 1
    rule_id = f"rule_{_rule_id_counter}"
    
    rule = AutoScalingRule(
        id=rule_id,
        name=request.name,
        pool_name=request.pool_name,
        enabled=request.enabled,
        trigger_type=request.trigger_type,
        cron_expression=request.cron_expression,
        timezone=request.timezone,
        metric=request.metric,
        threshold_high=request.threshold_high,
        threshold_low=request.threshold_low,
        cooldown_seconds=request.cooldown_seconds,
        action=request.action,
        target_count=request.target_count,
        scale_amount=request.scale_amount,
        min_agents=request.min_agents,
        max_agents=request.max_agents,
        role_type=request.role_type,
        created_at=datetime.utcnow(),
    )
    
    _auto_scaling_rules[rule_id] = rule
    logger.info(f"Auto-scaling rule created by {current_user.email}: {rule.name}")
    
    return rule


@router.get("/scaling/rules/{rule_id}")
async def get_auto_scaling_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
) -> AutoScalingRule:
    """Get a specific auto-scaling rule."""
    if rule_id not in _auto_scaling_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _auto_scaling_rules[rule_id]


@router.put("/scaling/rules/{rule_id}")
async def update_auto_scaling_rule(
    rule_id: str,
    request: AutoScalingRuleCreate,
    current_user: User = Depends(get_current_user),
) -> AutoScalingRule:
    """Update an auto-scaling rule."""
    if rule_id not in _auto_scaling_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    existing = _auto_scaling_rules[rule_id]
    
    rule = AutoScalingRule(
        id=rule_id,
        name=request.name,
        pool_name=request.pool_name,
        enabled=request.enabled,
        trigger_type=request.trigger_type,
        cron_expression=request.cron_expression,
        timezone=request.timezone,
        metric=request.metric,
        threshold_high=request.threshold_high,
        threshold_low=request.threshold_low,
        cooldown_seconds=request.cooldown_seconds,
        action=request.action,
        target_count=request.target_count,
        scale_amount=request.scale_amount,
        min_agents=request.min_agents,
        max_agents=request.max_agents,
        role_type=request.role_type,
        created_at=existing.created_at,
        last_triggered=existing.last_triggered,
    )
    
    _auto_scaling_rules[rule_id] = rule
    logger.info(f"Auto-scaling rule updated by {current_user.email}: {rule.name}")
    
    return rule


@router.delete("/scaling/rules/{rule_id}")
async def delete_auto_scaling_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete an auto-scaling rule."""
    if rule_id not in _auto_scaling_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = _auto_scaling_rules.pop(rule_id)
    logger.info(f"Auto-scaling rule deleted by {current_user.email}: {rule.name}")
    
    return {"message": f"Rule '{rule.name}' deleted"}


@router.post("/scaling/rules/{rule_id}/toggle")
async def toggle_auto_scaling_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
) -> AutoScalingRule:
    """Toggle an auto-scaling rule enabled/disabled."""
    if rule_id not in _auto_scaling_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = _auto_scaling_rules[rule_id]
    rule.enabled = not rule.enabled
    
    logger.info(
        f"Auto-scaling rule {'enabled' if rule.enabled else 'disabled'} "
        f"by {current_user.email}: {rule.name}"
    )
    
    return rule


@router.post("/scaling/rules/{rule_id}/trigger")
async def trigger_auto_scaling_rule(
    rule_id: str,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Manually trigger an auto-scaling rule."""
    if rule_id not in _auto_scaling_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = _auto_scaling_rules[rule_id]
    manager = _manager_registry.get(rule.pool_name)
    
    if not manager:
        raise HTTPException(
            status_code=404,
            detail=f"Pool '{rule.pool_name}' not found"
        )
    
    current_count = len(manager.agents)
    target_count = current_count
    
    # Calculate target based on action
    if rule.action == ScalingAction.SCALE_UP:
        target_count = min(current_count + rule.scale_amount, rule.max_agents)
    elif rule.action == ScalingAction.SCALE_DOWN:
        target_count = max(current_count - rule.scale_amount, rule.min_agents)
    elif rule.action == ScalingAction.SET_COUNT:
        target_count = max(rule.min_agents, min(rule.target_count or current_count, rule.max_agents))
    
    delta = target_count - current_count
    
    if delta == 0:
        return {
            "message": "No scaling needed",
            "current_count": current_count,
            "target_count": target_count,
            "action_taken": "none",
        }
    
    # Update last triggered
    rule.last_triggered = datetime.utcnow()
    
    if delta > 0:
        # Scale up - spawn agents
        # Note: In production, this would use bulk spawn with proper role handling
        return {
            "message": f"Would spawn {delta} agents (manual trigger)",
            "current_count": current_count,
            "target_count": target_count,
            "action_taken": "scale_up_requested",
            "agents_to_spawn": delta,
        }
    else:
        # Scale down - terminate agents
        agents_to_terminate = list(manager.agents.keys())[:abs(delta)]
        terminated = 0
        
        for agent_id in agents_to_terminate:
            try:
                await manager.terminate_agent(agent_id)
                terminated += 1
            except Exception as e:
                logger.error(f"Failed to terminate agent {agent_id}: {e}")
        
        return {
            "message": f"Terminated {terminated} agents",
            "current_count": current_count,
            "target_count": target_count,
            "action_taken": "scale_down",
            "agents_terminated": terminated,
        }


# ===== Phase 3: Agent Templates =====

class AgentTemplate(BaseModel):
    """Agent template for saving/restoring configurations."""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    # Agent configuration
    role_type: str
    pool_name: str
    # LLM Config
    llm_config: Dict[str, Any] = {}
    # Persona overrides
    persona_name: Optional[str] = None
    system_prompt_override: Optional[str] = None
    # Resource limits
    max_idle_time: int = 300
    heartbeat_interval: int = 30
    # Tags for organization
    tags: List[str] = []
    # Metadata
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    use_count: int = 0


class AgentTemplateCreate(BaseModel):
    """Request to create agent template."""
    name: str
    description: Optional[str] = None
    role_type: str
    pool_name: str = "universal_pool"
    llm_config: Dict[str, Any] = {}
    persona_name: Optional[str] = None
    system_prompt_override: Optional[str] = None
    max_idle_time: int = 300
    heartbeat_interval: int = 30
    tags: List[str] = []


class AgentTemplateFromAgent(BaseModel):
    """Request to create template from existing agent."""
    agent_id: str
    template_name: str
    description: Optional[str] = None
    tags: List[str] = []


# In-memory storage for agent templates
_agent_templates: Dict[str, AgentTemplate] = {}
_template_id_counter = 0


@router.get("/templates")
async def list_agent_templates(
    role_type: Optional[str] = None,
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> List[AgentTemplate]:
    """List all agent templates."""
    templates = list(_agent_templates.values())
    
    if role_type:
        templates = [t for t in templates if t.role_type == role_type]
    
    if tag:
        templates = [t for t in templates if tag in t.tags]
    
    # Sort by use count (most used first)
    templates.sort(key=lambda t: t.use_count, reverse=True)
    
    return templates


@router.post("/templates")
async def create_agent_template(
    request: AgentTemplateCreate,
    current_user: User = Depends(get_current_user),
) -> AgentTemplate:
    """Create a new agent template."""
    global _template_id_counter
    
    # Validate role type
    role_class_map = get_role_class_map()
    if request.role_type not in role_class_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role_type. Valid: {list(role_class_map.keys())}"
        )
    
    _template_id_counter += 1
    template_id = f"template_{_template_id_counter}"
    
    template = AgentTemplate(
        id=template_id,
        name=request.name,
        description=request.description,
        role_type=request.role_type,
        pool_name=request.pool_name,
        llm_config=request.llm_config,
        persona_name=request.persona_name,
        system_prompt_override=request.system_prompt_override,
        max_idle_time=request.max_idle_time,
        heartbeat_interval=request.heartbeat_interval,
        tags=request.tags,
        created_by=current_user.email,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    _agent_templates[template_id] = template
    logger.info(f"Agent template created by {current_user.email}: {template.name}")
    
    return template


@router.post("/templates/from-agent")
async def create_template_from_agent(
    request: AgentTemplateFromAgent,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentTemplate:
    """Create a template from an existing agent's configuration."""
    global _template_id_counter
    
    # Find agent in database
    agent_uuid = UUID(request.agent_id)
    db_agent = session.get(Agent, agent_uuid)
    
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Find which pool the agent is in
    pool_name = "universal_pool"
    for pname, manager in _manager_registry.items():
        if agent_uuid in manager.agents:
            pool_name = pname
            break
    
    # Extract LLM config from persona metadata
    llm_config = {}
    if db_agent.persona_metadata:
        llm_config = db_agent.persona_metadata.get("llm_config", {})
    
    _template_id_counter += 1
    template_id = f"template_{_template_id_counter}"
    
    template = AgentTemplate(
        id=template_id,
        name=request.template_name,
        description=request.description or f"Template from agent {db_agent.human_name}",
        role_type=db_agent.role_type,
        pool_name=pool_name,
        llm_config=llm_config,
        persona_name=db_agent.human_name,
        system_prompt_override=db_agent.persona_metadata.get("system_prompt_override") if db_agent.persona_metadata else None,
        tags=request.tags,
        created_by=current_user.email,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    _agent_templates[template_id] = template
    logger.info(f"Agent template created from agent {request.agent_id} by {current_user.email}")
    
    return template


@router.get("/templates/{template_id}")
async def get_agent_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
) -> AgentTemplate:
    """Get a specific agent template."""
    if template_id not in _agent_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    return _agent_templates[template_id]


@router.put("/templates/{template_id}")
async def update_agent_template(
    template_id: str,
    request: AgentTemplateCreate,
    current_user: User = Depends(get_current_user),
) -> AgentTemplate:
    """Update an agent template."""
    if template_id not in _agent_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    existing = _agent_templates[template_id]
    
    template = AgentTemplate(
        id=template_id,
        name=request.name,
        description=request.description,
        role_type=request.role_type,
        pool_name=request.pool_name,
        llm_config=request.llm_config,
        persona_name=request.persona_name,
        system_prompt_override=request.system_prompt_override,
        max_idle_time=request.max_idle_time,
        heartbeat_interval=request.heartbeat_interval,
        tags=request.tags,
        created_by=existing.created_by,
        created_at=existing.created_at,
        updated_at=datetime.utcnow(),
        use_count=existing.use_count,
    )
    
    _agent_templates[template_id] = template
    logger.info(f"Agent template updated by {current_user.email}: {template.name}")
    
    return template


@router.delete("/templates/{template_id}")
async def delete_agent_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete an agent template."""
    if template_id not in _agent_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = _agent_templates.pop(template_id)
    logger.info(f"Agent template deleted by {current_user.email}: {template.name}")
    
    return {"message": f"Template '{template.name}' deleted"}


@router.post("/templates/{template_id}/spawn")
async def spawn_from_template(
    template_id: str,
    project_id: str,
    count: int = 1,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Spawn one or more agents from a template."""
    if template_id not in _agent_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = _agent_templates[template_id]
    
    # Get manager
    manager = _manager_registry.get(template.pool_name)
    if not manager:
        raise HTTPException(
            status_code=404,
            detail=f"Pool '{template.pool_name}' not found"
        )
    
    # Check capacity
    available_slots = manager.max_agents - len(manager.agents)
    if available_slots < count:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough capacity. Available: {available_slots}, Requested: {count}"
        )
    
    role_class_map = get_role_class_map()
    role_class = role_class_map.get(template.role_type)
    if not role_class:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role_type in template: {template.role_type}"
        )
    
    from app.services.persona_service import PersonaService
    from app.services.agent_service import AgentService
    
    persona_service = PersonaService(session)
    agent_service = AgentService(session)
    project_uuid = UUID(project_id)
    
    results = []
    success_count = 0
    
    for i in range(count):
        try:
            # Get persona
            persona = persona_service.get_random_persona_for_role(
                role_type=template.role_type,
                exclude_ids=[]
            )
            
            if not persona:
                results.append({
                    "index": i,
                    "status": "error",
                    "error": f"No persona found for {template.role_type}",
                })
                continue
            
            # Create agent
            db_agent = agent_service.create_from_template(
                project_id=project_uuid,
                persona_template=persona
            )
            
            # Apply template config
            if template.llm_config or template.system_prompt_override:
                if not db_agent.persona_metadata:
                    db_agent.persona_metadata = {}
                if template.llm_config:
                    db_agent.persona_metadata["llm_config"] = template.llm_config
                if template.system_prompt_override:
                    db_agent.persona_metadata["system_prompt_override"] = template.system_prompt_override
                session.add(db_agent)
            
            # Spawn agent
            success = await manager.spawn_agent(
                agent_id=db_agent.id,
                role_class=role_class,
                heartbeat_interval=template.heartbeat_interval,
                max_idle_time=template.max_idle_time,
            )
            
            if success:
                success_count += 1
                results.append({
                    "index": i,
                    "agent_id": str(db_agent.id),
                    "agent_name": db_agent.human_name,
                    "status": "spawned",
                })
            else:
                session.delete(db_agent)
                results.append({
                    "index": i,
                    "status": "spawn_failed",
                    "error": "Failed to spawn agent",
                })
                
        except Exception as e:
            results.append({
                "index": i,
                "status": "error",
                "error": str(e),
            })
    
    session.commit()
    
    # Increment use count
    template.use_count += success_count
    
    logger.info(
        f"Spawned {success_count} agents from template '{template.name}' "
        f"by {current_user.email}"
    )
    
    return {
        "message": f"Spawned {success_count} of {count} agents from template '{template.name}'",
        "success_count": success_count,
        "failed_count": count - success_count,
        "results": results,
        "template": template,
    }


@router.post("/templates/{template_id}/duplicate")
async def duplicate_agent_template(
    template_id: str,
    new_name: str,
    current_user: User = Depends(get_current_user),
) -> AgentTemplate:
    """Duplicate an existing template with a new name."""
    global _template_id_counter
    
    if template_id not in _agent_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    source = _agent_templates[template_id]
    
    _template_id_counter += 1
    new_template_id = f"template_{_template_id_counter}"
    
    template = AgentTemplate(
        id=new_template_id,
        name=new_name,
        description=f"Copy of {source.name}" + (f": {source.description}" if source.description else ""),
        role_type=source.role_type,
        pool_name=source.pool_name,
        llm_config=source.llm_config.copy(),
        persona_name=source.persona_name,
        system_prompt_override=source.system_prompt_override,
        max_idle_time=source.max_idle_time,
        heartbeat_interval=source.heartbeat_interval,
        tags=source.tags.copy(),
        created_by=current_user.email,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        use_count=0,
    )
    
    _agent_templates[new_template_id] = template
    logger.info(f"Agent template duplicated by {current_user.email}: {source.name} -> {new_name}")
    
    return template
