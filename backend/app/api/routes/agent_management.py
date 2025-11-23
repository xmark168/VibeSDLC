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
from app.agents.core.redis_client import init_redis, close_redis, get_redis_client
from app.agents.core.name_generator import generate_agent_name, get_display_name

# Import role classes (NOT crew classes - Role classes wrap Crews and handle lifecycle)
from app.agents.roles.team_leader import TeamLeaderRole
from app.agents.roles.business_analyst import BusinessAnalystRole
from app.agents.roles.developer import DeveloperRole
from app.agents.roles.tester import TesterRole

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
    """Pool information response."""
    pool_name: str
    role_class: str
    total_agents: int
    active_agents: int
    busy_agents: int
    idle_agents: int
    total_spawned: int
    total_terminated: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    load: float
    created_at: str


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

# Manager registry - manages auto-scaling pools with multiprocessing
_manager_registry: Dict[str, AgentPoolManager] = {}

# Role class mapping (use Role classes, NOT Crew classes)
# Role classes handle lifecycle, consumers, and wrap Crew functionality
ROLE_CLASS_MAP = {
    "team_leader": TeamLeaderRole,
    "business_analyst": BusinessAnalystRole,
    "developer": DeveloperRole,
    "tester": TesterRole,
}


async def initialize_default_pools() -> None:
    """Initialize default agent pools for all role types.

    Creates AgentPoolManager instances that:
    - Spawn worker processes dynamically
    - Auto-restore agents from database on startup
    - Auto-scale by spawning new workers when capacity is reached (10 agents/process)
    """
    import logging
    from sqlmodel import Session, select
    from app.core.db import engine

    logger = logging.getLogger(__name__)

    # Initialize Redis (required for multiprocessing mode)
    logger.info("Initializing Redis for multiprocessing agent pools...")
    if not await init_redis():
        raise RuntimeError(
            "Failed to connect to Redis. Redis is required for multiprocessing mode.\n"
            "Please ensure Redis is running: docker-compose up -d redis"
        )

    logger.info("✓ Redis connected successfully")

    default_pools = [
        {"role_type": "team_leader", "pool_name": "team_leader_pool"},
        {"role_type": "business_analyst", "pool_name": "business_analyst_pool"},
        {"role_type": "developer", "pool_name": "developer_pool"},
        {"role_type": "tester", "pool_name": "tester_pool"},
    ]

    for pool_config in default_pools:
        role_type = pool_config["role_type"]
        pool_name = pool_config["pool_name"]
        role_class = ROLE_CLASS_MAP[role_type]

        # Skip if manager already exists
        if pool_name in _manager_registry:
            logger.info(f"Manager '{pool_name}' already exists, skipping")
            continue

        try:
            # Create AgentPoolManager
            manager = AgentPoolManager(
                pool_name=pool_name,
                role_class=role_class,
                max_agents_per_process=10,
                heartbeat_interval=30,
            )

            # Start manager
            if await manager.start():
                _manager_registry[pool_name] = manager
                logger.info(f"✓ Created manager: {pool_name} ({role_type})")

                # Restore agents from database
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
                        .where(
                            Agent.role_type == role_type,
                            Agent.status.in_(reset_states)
                        )
                        .values(status=AgentStatus.idle)
                    )
                    reset_result = db_session.exec(reset_stmt)
                    db_session.commit()

                    if reset_result.rowcount > 0:
                        logger.info(
                            f"Auto-reset {reset_result.rowcount} {role_type} agents "
                            f"from problematic states to idle"
                        )

                    # Query agents to restore
                    agents_query = select(Agent).where(
                        Agent.role_type == role_type,
                        Agent.status.in_([AgentStatus.idle, AgentStatus.stopped])
                    )
                    db_agents = db_session.exec(agents_query).all()

                    logger.info(
                        f"Restoring {len(db_agents)} {role_type} agents "
                        f"(workers will auto-spawn as needed)..."
                    )

                    # Spawn agents via manager (auto-scales workers)
                    for db_agent in db_agents:
                        try:
                            success = await manager.spawn_agent(
                                agent_id=db_agent.id,
                                heartbeat_interval=30,
                                max_idle_time=300,
                            )

                            if success:
                                db_agent.status = AgentStatus.idle
                                db_session.add(db_agent)
                                logger.debug(f"  ✓ Queued: {db_agent.human_name}")
                            else:
                                logger.warning(f"  ✗ Failed: {db_agent.human_name}")

                        except Exception as e:
                            logger.error(f"Error restoring {db_agent.human_name}: {e}")

                    db_session.commit()

                    logger.info(
                        f"📊 Queued {len(db_agents)} {role_type} agents for restoration"
                    )

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
    # Validate role type
    if request.role_type not in ROLE_CLASS_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role_type. Must be one of: {list(ROLE_CLASS_MAP.keys())}"
        )

    # Check if pool manager already exists
    if request.pool_name in _manager_registry:
        raise HTTPException(status_code=400, detail=f"Pool manager '{request.pool_name}' already exists")

    # Extract max_agents if provided (default 10)
    max_agents_per_process = 10
    if request.config:
        max_agents_per_process = request.config.max_agents

    # Create pool manager
    role_class = ROLE_CLASS_MAP[request.role_type]
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

    Creates agent in database then sends spawn command to AgentPoolManager.
    Manager auto-scales workers and routes spawn request to available worker.
    """
    # Validate role type
    if request.role_type not in ROLE_CLASS_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role_type. Must be one of: {list(ROLE_CLASS_MAP.keys())}"
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

    # Get manager and spawn via multiprocessing
    manager = get_manager(request.pool_name)

    # Spawn via manager (auto-scales workers)
    success = await manager.spawn_agent(
        agent_id=db_agent.id,
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
        "pool_name": request.pool_name,
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

    Sends terminate command to AgentPoolManager which routes to appropriate worker.
    """
    manager = get_manager(request.pool_name)

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
