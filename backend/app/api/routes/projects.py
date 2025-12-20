"""Project management API."""
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks
from sqlmodel import select
from app.api.deps import CurrentUser, SessionDep
from app.services import ProjectService
from app.services.agent_service import AgentService
from app.models import Project, Role, Agent, AgentStatus, Subscription, Plan
from app.schemas import ProjectCreate, ProjectUpdate, ProjectPublic, ProjectsPublic
from app.services.persona_service import PersonaService
from app.utils.seed_techstacks import copy_boilerplate_to_project, init_git_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])

# Default role types for new projects
DEFAULT_AGENT_ROLES = ["team_leader", "business_analyst", "developer", "tester"]


@router.get("/{project_id}/token-budget")
async def get_project_token_budget(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Get token budget status for a project.
    
    Returns daily and monthly token usage and limits.
    """
    # Force reload trigger
    from app.services.singletons import get_token_budget_service
    
    # Check project exists and user has access
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.owner_id != current_user.id and current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    # Get budget status
    budget_service = await get_token_budget_service()
    budget_status = await budget_service.get_budget_status(project_id)
    
    if "error" in budget_status:
        raise HTTPException(status_code=500, detail=budget_status["error"])
    
    return budget_status


@router.get("/", response_model=ProjectsPublic)
def list_projects(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> ProjectsPublic:
    """
    Get all projects owned by the current user, or all projects if admin.

    Args:
        session: Database session
        current_user: Current authenticated user
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return

    Returns:
        ProjectsPublic: List of projects with total count
    """
    project_service = ProjectService(session)
    if current_user.role == Role.ADMIN:
        projects, total_count = project_service.get_all(
            skip=skip,
            limit=limit,
        )
    else:
        projects, total_count = project_service.get_by_owner(
            owner_id=current_user.id,
            skip=skip,
            limit=limit,
        )

    return ProjectsPublic(
        data=[ProjectPublic.model_validate(p) for p in projects],
        count=total_count,
    )


@router.get("/{project_id}", response_model=ProjectPublic)
def get_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectPublic:
    """
    Get a specific project by ID.

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user

    Returns:
        ProjectPublic: Project details

    Raises:
        HTTPException: If project not found or user lacks access
    """
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

    if not project:
        logger.warning(f"Project {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user owns the project or is admin
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to access project {project_id} "
            f"owned by {project.owner_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    return ProjectPublic.model_validate(project)


@router.post("/", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectPublic:
    """
    Create a new project.

    The project code is automatically generated in format PRJ-001, PRJ-002, etc.
    Default agents (1 per role type) are automatically created for the project.

    Uses a single transaction - if agent creation fails, the project is rolled back.

    Args:
        project_in: Project creation schema
        session: Database session
        current_user: Current authenticated user

    Returns:
        ProjectPublic: Created project details

    Raises:
        HTTPException: If project or agent creation fails
    """
    logger.info(f"Creating new project '{project_in.name}' for user {current_user.id}")

    # Check project limit based on user's subscription plan
    now = datetime.now(timezone.utc)
    
    # Get user's active subscription
    subscription_statement = (
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == "active")
        .where(Subscription.end_at > now)
    )
    subscription = session.exec(subscription_statement).first()
    
    # Determine project limit from plan
    if subscription:
        plan = session.get(Plan, subscription.plan_id)
        project_limit = plan.available_project if plan else None
    else:
        # No active subscription - use FREE plan limit
        free_plan_statement = select(Plan).where(Plan.code == "FREE")
        free_plan = session.exec(free_plan_statement).first()
        project_limit = free_plan.available_project if free_plan else 1  # Default to 1 for safety
    
    # Check if user has reached project limit (skip for admins and unlimited plans)
    if current_user.role != Role.ADMIN and project_limit is not None and project_limit != -1:
        # Count user's current projects
        project_service = ProjectService(session)
        _, current_project_count = project_service.get_by_owner(
            owner_id=current_user.id,
            skip=0,
            limit=1,  # We only need the count
        )
        
        if current_project_count >= project_limit:
            plan_name = "FREE" if not subscription else (plan.name if plan else "Unknown")
            logger.warning(
                f"User {current_user.id} reached project limit ({current_project_count}/{project_limit}) "
                f"on {plan_name} plan"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You have reached your project limit ({project_limit} projects) on your current plan. Please upgrade to create more projects.",
            )

    try:
        # Create project without committing (uses flush to get ID)
        project_service = ProjectService(session)
        project = project_service.create_no_commit(
            project_in=project_in,
            owner_id=current_user.id,
        )

        # Auto-generate project_path: projects/{project_id}
        project.project_path = f"projects/{project.id}"

        # Copy boilerplate based on tech_stack
        tech_stack = project.tech_stack or "nodejs-react"
        backend_root = Path(__file__).resolve().parent.parent.parent.parent
        project_path = backend_root / "projects" / str(project.id)
        
        if copy_boilerplate_to_project(tech_stack, project_path):
            init_git_repo(project_path)
            logger.info(f"Copied boilerplate '{tech_stack}' to {project_path}")
        else:
            # Fallback: just create empty folder
            project_path.mkdir(parents=True, exist_ok=True)
            logger.warning(f"No boilerplate for '{tech_stack}', created empty folder")

        # Auto-create default agents for the project with diverse personas
        persona_service = PersonaService(session)
        agent_service = AgentService(session)
        created_agents = []
        used_persona_ids = []
        
        for role_type in DEFAULT_AGENT_ROLES:
            persona = None
            
            # Check if user selected custom persona for this role
            if project_in.agent_personas and role_type in project_in.agent_personas:
                custom_persona_id = project_in.agent_personas[role_type]
                if custom_persona_id:
                    persona = persona_service.get_by_id(UUID(custom_persona_id))
                    if persona:
                        logger.info(f"Using custom persona '{persona.name}' for {role_type}")
            
            # Fallback to random persona if no custom selection or not found
            if not persona:
                persona = persona_service.get_random_persona_for_role(
                    role_type=role_type,
                    exclude_ids=used_persona_ids
                )
            
            if not persona:
                # No fallback - fail fast if personas not seeded
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"No persona templates found for role '{role_type}'. Please seed persona templates first by running: python app/db/seed_personas_script.py"
                )
            
            # Create agent from persona template
            agent = agent_service.create_from_template(
                project_id=project.id,
                persona_template=persona
            )
            used_persona_ids.append(persona.id)
            created_agents.append(agent)
            
            logger.info(
                f"✓ Created {agent.human_name} ({role_type}) "
                f"with persona: {persona.communication_style}, traits: {', '.join(persona.personality_traits[:2]) if persona.personality_traits else 'default'}"
            )

        # Commit both project and agents in a single transaction
        session.commit()
        session.refresh(project)

        logger.info(
            f"Project created successfully: {project.code} (ID: {project.id}) "
            f"with {len(created_agents)} agents"
        )
        
        # Auto-spawn agents after project creation
        from app.services.agent_pool_service import AgentPoolService
        
        role_class_map = AgentPoolService.get_role_class_map()
        spawned_count = 0
        
        for agent in created_agents:
            # Get pool for this agent's role (role-specific > universal > any)
            pool_manager = AgentPoolService.get_available_pool(role_type=agent.role_type)
            if not pool_manager:
                logger.warning(f"No pool available for {agent.role_type}, skipping spawn")
                continue
            
            role_class = role_class_map.get(agent.role_type)
            if not role_class:
                logger.warning(f"No role class found for {agent.role_type}, skipping spawn")
                continue
            
            try:
                success = await pool_manager.spawn_agent(
                    agent_id=agent.id,
                    role_class=role_class,
                    heartbeat_interval=30,
                    max_idle_time=300,
                )
                if success:
                    spawned_count += 1
                    logger.info(f"✓ Spawned agent {agent.human_name} ({agent.role_type}) in {pool_manager.pool_name}")
                else:
                    logger.warning(f"Failed to spawn agent {agent.human_name}")
            except Exception as e:
                logger.error(f"Error spawning agent {agent.human_name}: {e}")
        
        logger.info(f"Auto-spawned {spawned_count}/{len(created_agents)} agents for project {project.code}")
        
        return ProjectPublic.model_validate(project)

    except Exception as e:
        # Rollback the entire transaction (project + agents)
        session.rollback()
        logger.error(f"Failed to create project '{project_in.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@router.put("/{project_id}", response_model=ProjectPublic)
def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectPublic:
    """
    Update a project.

    Args:
        project_id: UUID of the project to update
        project_in: Project update schema
        session: Database session
        current_user: Current authenticated user

    Returns:
        ProjectPublic: Updated project details

    Raises:
        HTTPException: If project not found or user lacks access
    """
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

    if not project:
        logger.warning(f"Project {project_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user owns the project or is admin
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to update project {project_id} "
            f"owned by {project.owner_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    logger.info(f"Updating project {project.code} (ID: {project_id})")

    project_service = ProjectService(session)
    updated_project = project_service.update(
        db_project=project,
        project_in=project_in,
    )

    return ProjectPublic.model_validate(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> None:
    """
    Delete a project and clean up all associated files (workspace + worktrees).
    File cleanup runs in background for faster response.

    Args:
        project_id: UUID of the project to delete
        session: Database session
        current_user: Current authenticated user
        background_tasks: FastAPI background tasks

    Raises:
        HTTPException: If project not found or user lacks access
    """
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

    if not project:
        logger.warning(f"Project {project_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user owns the project or is admin
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to delete project {project_id} "
            f"owned by {project.owner_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    logger.info(f"Deleting project {project.code} (ID: {project_id})")
    
    # Get project path before deletion for background cleanup
    project_path = project.project_path
    project_code = project.code
    
    # Collect agent info for background termination
    agents_info = [
        {"id": str(agent.id), "role_type": agent.role_type, "human_name": agent.human_name}
        for agent in session.query(Agent).filter(Agent.project_id == project_id).all()
    ]
    
    # Delete from database first (fast) - this makes the project disappear from UI immediately
    project_service.delete(project_id)
    
    # Schedule background cleanup tasks
    background_tasks.add_task(
        _cleanup_project_files_and_agents,
        project_path=project_path,
        project_code=project_code,
        agents_info=agents_info,
    )


async def _cleanup_project_files_and_agents(
    project_path: str | None,
    project_code: str,
    agents_info: list[dict],
) -> None:
    """Background task to clean up project files and terminate agents."""
    import shutil
    import stat
    import os
    import asyncio
    
    logger.info(f"[Background] Starting cleanup for project {project_code}")
    
    # Terminate agents in parallel
    if agents_info:
        from app.services.agent_pool_service import AgentPoolService
        
        async def terminate_agent(agent: dict):
            pool_manager = AgentPoolService.get_available_pool(role_type=agent["role_type"])
            if pool_manager:
                try:
                    await pool_manager.terminate_agent(agent["id"])
                    logger.info(f"[Background] Stopped agent {agent['human_name']}")
                except Exception as e:
                    logger.warning(f"[Background] Failed to stop agent {agent['human_name']}: {e}")
        
        await asyncio.gather(*[terminate_agent(a) for a in agents_info], return_exceptions=True)
    
    # Clean up project files
    if project_path:
        backend_root = Path(__file__).resolve().parent.parent.parent.parent
        project_dir = backend_root / project_path
        
        def remove_readonly(func, path, excinfo):
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            func(path)
        
        if project_dir.exists():
            try:
                # Remove large subdirectories first
                for subdir in ['.next', 'node_modules', '.worktrees']:
                    subpath = project_dir / subdir
                    if subpath.exists():
                        shutil.rmtree(subpath, onerror=remove_readonly)
                
                # Remove main directory
                shutil.rmtree(project_dir, onerror=remove_readonly)
                logger.info(f"[Background] Deleted project directory: {project_dir}")
            except Exception as e:
                logger.warning(f"[Background] Failed to delete project directory: {e}")


@router.post("/{project_id}/cleanup", status_code=status.HTTP_200_OK)
def cleanup_project_worktrees(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """
    Clean up all worktrees for a project (without deleting the project).

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user

    Returns:
        dict: Cleanup result with count of deleted worktrees
    """
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    deleted_count = project_service.cleanup_worktrees(project_id)
    
    return {
        "message": f"Cleaned up {deleted_count} worktrees",
        "deleted_count": deleted_count,
        "project_id": str(project_id),
    }


@router.get("/{project_id}/deletion-preview", status_code=status.HTTP_200_OK)
def preview_project_deletion(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """
    Preview what data will be deleted when deleting a project.
    
    Returns counts of all related entities that will be cascade deleted.
    """
    from sqlmodel import select, func
    from app.models import Story, Message, Artifact, Epic
    from app.models.execution import AgentExecution
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )
    
    # Count all related data
    agents_count = session.exec(
        select(func.count(Agent.id)).where(Agent.project_id == project_id)
    ).one()
    
    stories_count = session.exec(
        select(func.count(Story.id)).where(Story.project_id == project_id)
    ).one()
    
    messages_count = session.exec(
        select(func.count(Message.id)).where(Message.project_id == project_id)
    ).one()
    
    epics_count = session.exec(
        select(func.count(Epic.id)).where(Epic.project_id == project_id)
    ).one()
    
    executions_count = session.exec(
        select(func.count(AgentExecution.id)).where(AgentExecution.project_id == project_id)
    ).one()
    
    artifacts_count = session.exec(
        select(func.count(Artifact.id)).where(Artifact.project_id == project_id)
    ).one()
    
    return {
        "project_id": str(project_id),
        "project_name": project.name,
        "project_code": project.code,
        "counts": {
            "agents": agents_count,
            "stories": stories_count,
            "epics": epics_count,
            "messages": messages_count,
            "executions": executions_count,
            "artifacts": artifacts_count,
        },
        "has_workspace": bool(project.project_path),
        "workspace_path": project.project_path,
    }


# ============= Dev Server Endpoints =============

def _cleanup_dev_server(workspace_path: Path, port: int = None, pid: int = None) -> None:
    """Clean up dev server processes and lock files.
    
    SAFETY: Only kills processes by specific PID or port.
    Does NOT use pkill which could kill all Node processes system-wide.
    """
    import subprocess
    import signal
    import time
    
    # Kill by PID (graceful then force)
    if pid:
        try:
            # Try graceful shutdown first
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to process PID {pid}")
            time.sleep(0.5)
            
            # Force kill if still alive
            try:
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Force killed process PID {pid}")
            except ProcessLookupError:
                logger.debug(f"Process {pid} already terminated")
        except ProcessLookupError:
            logger.debug(f"Process {pid} not found")
        except Exception as e:
            logger.warning(f"Failed to kill process {pid}: {e}")
    
    # Kill by port using lsof (graceful then force)
    if port:
        try:
            # Find PIDs using the port
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                
                # Graceful shutdown first
                for pid_str in pids:
                    try:
                        pid_int = int(pid_str)
                        os.kill(pid_int, signal.SIGTERM)
                        logger.info(f"Sent SIGTERM to process on port {port}: PID {pid_str}")
                    except:
                        pass
                
                # Wait for graceful shutdown
                time.sleep(0.5)
                
                # Force kill if still alive
                result2 = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True, text=True, timeout=5
                )
                if result2.stdout.strip():
                    for pid_str in result2.stdout.strip().split('\n'):
                        try:
                            os.kill(int(pid_str), signal.SIGKILL)
                            logger.info(f"Force killed process on port {port}: PID {pid_str}")
                        except:
                            pass
        except Exception as e:
            logger.warning(f"Failed to kill processes on port {port}: {e}")
    
    # Clean up Next.js artifacts (file cleanup only, NO process killing)
    if workspace_path and workspace_path.exists():
        # Remove lock file
        lock_file = workspace_path / ".next" / "dev" / "lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
                logger.info("Removed Next.js lock file")
            except Exception as e:
                logger.warning(f"Failed to remove lock file: {e}")
        
        # Remove trace file that can cause issues
        trace_dir = workspace_path / ".next" / "trace"
        if trace_dir.exists():
            try:
                import shutil
                shutil.rmtree(trace_dir, ignore_errors=True)
                logger.info("Removed Next.js trace directory")
            except Exception:
                pass
    
    # NOTE: Removed kill_processes_using_directory() call - DANGEROUS!
    # Old code used 'pkill -9 -f node|pnpm' which kills ALL node processes system-wide,
    # including backend server, other projects, and system tools.
    # PID and port-based killing is sufficient and safe.


@router.post("/{project_id}/dev-server/start")
async def start_project_dev_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID
) -> Any:
    """Start dev server for project main workspace."""
    import subprocess
    import socket
    import sys
    import asyncio
    import time
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.project_path:
        raise HTTPException(status_code=400, detail="No workspace path for this project")
    
    # Get absolute workspace path
    workspace_path = _get_workspace_path(project.project_path)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=400, detail=f"Project workspace not found: {workspace_path}")
    
    # Helper: Find free port
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    # Helper: Wait for port async
    async def wait_for_port_async(port: int, timeout: float = 30.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(('127.0.0.1', port))
                    return True
            except (socket.error, socket.timeout):
                await asyncio.sleep(1.0)  # Increased from 0.5s - reduce CPU usage
        return False
    
    # ===== CLEANUP: Always clean up before starting =====
    logger.info(f"Cleaning up existing dev server for project {project_id}...")
    _cleanup_dev_server(
        workspace_path=workspace_path,
        port=project.dev_server_port,
        pid=project.dev_server_pid
    )
    await asyncio.sleep(0.1)  # Reduced from 0.5s
    
    # ===== 0. Ensure next.config.ts has iframe headers =====
    next_config_path = workspace_path / "next.config.ts"
    if next_config_path.exists():
        try:
            config_content = next_config_path.read_text(encoding='utf-8')
            if 'frame-ancestors' not in config_content:
                # Add headers config before the closing bracket
                headers_config = '''
  // Allow embedding in iframe for App Preview
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'Content-Security-Policy',
            value: "frame-ancestors 'self' http://localhost:* http://127.0.0.1:*",
          },
        ],
      },
    ];
  },'''
                # Insert before "};'
                if '};\n' in config_content:
                    config_content = config_content.replace('};\n', headers_config + '\n};\n')
                elif '};\r\n' in config_content:
                    config_content = config_content.replace('};\r\n', headers_config + '\n};\r\n')
                next_config_path.write_text(config_content, encoding='utf-8')
                logger.info("Added iframe headers to next.config.ts")
        except Exception as e:
            logger.warning(f"Failed to update next.config.ts: {e}")
    
    # Helper to broadcast log to frontend
    async def broadcast_log(message: str, status: str = "running"):
        from app.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project({
            "type": "dev_server_log",
            "project_id": str(project_id),
            "message": message,
            "status": status,  # "running", "success", "error"
        }, project_id)
    
    # ===== 1. Start PostgreSQL container if project uses Prisma =====
    prisma_schema = workspace_path / "prisma" / "schema.prisma"
    if prisma_schema.exists():
        await broadcast_log("Starting PostgreSQL database...", "running")
        logger.info(f"Prisma schema found, starting PostgreSQL container...")
        try:
            from app.agents.developer.src.utils.db_container import (
                start_postgres_container,
                update_env_file,
            )
            
            container_info = start_postgres_container(str(project_id))
            if container_info:
                # Update .env with DATABASE_URL
                update_env_file(str(workspace_path), str(project_id))
                
                # Store container info in project
                project.db_container_id = container_info.get("container_id")
                project.db_port = int(container_info.get("port", 0)) if container_info.get("port") else None
                session.add(project)
                session.commit()
                await broadcast_log(f"Database ready on port {container_info.get('port')}", "success")
                logger.info(f"PostgreSQL container started on port {container_info.get('port')}")
        except Exception as e:
            await broadcast_log(f"Database setup failed: {str(e)[:100]}", "error")
            logger.warning(f"Failed to start PostgreSQL container: {e}")
    
    # ===== 2. Check if node_modules exists, if not run pnpm install =====
    node_modules_path = workspace_path / "node_modules"
    if not node_modules_path.exists():
        await broadcast_log("Installing dependencies (this may take a few minutes)...", "running")
        logger.info(f"node_modules not found, running pnpm install...")
        # Run in thread to avoid blocking event loop (can take 5+ minutes)
        install_result = await asyncio.to_thread(
            subprocess.run,
            ["pnpm", "install"],
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutes timeout (reduced from 5 min)
        )
        if install_result.returncode != 0:
            await broadcast_log("Failed to install dependencies", "error")
            logger.error(f"pnpm install failed: {install_result.stderr}")
            raise HTTPException(status_code=500, detail=f"Failed to install dependencies: {install_result.stderr[:500]}")
        await broadcast_log("Dependencies installed", "success")
        logger.info("pnpm install completed")
    
    # ===== 3. Run Prisma migrations if schema exists =====
    if prisma_schema.exists():
        await broadcast_log("Setting up database schema...", "running")
        logger.info("Running Prisma db push...")
        try:
            # Push schema to database
            db_push_result = await asyncio.to_thread(
                subprocess.run,
                ["pnpm", "prisma", "db", "push", "--skip-generate"],
                cwd=str(workspace_path),
                capture_output=True,
                text=True,
                timeout=45,  # Reduced from 60s
            )
            if db_push_result.returncode == 0:
                await broadcast_log("Database schema ready", "success")
                logger.info("Prisma db push completed")
            else:
                await broadcast_log("Database schema setup had warnings", "error")
                logger.warning(f"Prisma db push failed: {db_push_result.stderr}")
            
            # Generate Prisma client
            await broadcast_log("Generating Prisma client...", "running")
            logger.info("Running Prisma generate...")
            generate_result = await asyncio.to_thread(
                subprocess.run,
                ["pnpm", "prisma", "generate"],
                cwd=str(workspace_path),
                capture_output=True,
                text=True,
                timeout=45,  # Reduced from 60s
            )
            if generate_result.returncode == 0:
                await broadcast_log("Prisma client generated", "success")
                logger.info("Prisma generate completed")
            else:
                logger.warning(f"Prisma generate failed: {generate_result.stderr}")
            
            # Run seed if exists and generate succeeded (same command as run_code.py)
            seed_file = workspace_path / "prisma" / "seed.ts"
            seed_file_js = workspace_path / "prisma" / "seed.js"
            if generate_result.returncode == 0 and (seed_file.exists() or seed_file_js.exists()):
                await broadcast_log("Seeding database...", "running")
                logger.info("Running database seed...")
                
                # Use prisma db seed - works on all platforms
                if seed_file.exists():
                    seed_args = "pnpm prisma db seed"
                else:
                    seed_args = "node prisma/seed.js"
                use_shell = True
                
                seed_result = await asyncio.to_thread(
                    subprocess.run,
                    seed_args,
                    cwd=str(workspace_path),
                    shell=use_shell,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if seed_result.returncode == 0:
                    await broadcast_log("Database seeded", "success")
                    logger.info(f"Database seed completed: {seed_result.stdout}")
                else:
                    error_msg = seed_result.stderr or seed_result.stdout or "Unknown error"
                    await broadcast_log(f"Database seed failed", "error")
                    logger.warning(f"Database seed failed: {error_msg}")
        except Exception as e:
            await broadcast_log(f"Prisma setup failed", "error")
            logger.warning(f"Prisma setup failed: {e}")
    
    port = find_free_port()
    await broadcast_log("Starting development server...", "running")
    logger.info(f"Starting dev server for project {project_id} on port {port}")
    
    # Retry logic (same as story dev server)
    max_attempts = 3
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            process = subprocess.Popen(
                ["pnpm", "dev", "--port", str(port), "--hostname", "0.0.0.0"],
                cwd=str(workspace_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                env={**os.environ, "FORCE_COLOR": "0"},
            )
            
            # Wait for port to be ready
            await broadcast_log(f"Waiting for server to be ready on port {port}...")
            logger.info(f"Waiting for dev server on port {port}...")
            
            if await wait_for_port_async(port, timeout=30.0) and process.poll() is None:  # Reduced from 60s
                # Store in project
                project.dev_server_port = port
                project.dev_server_pid = process.pid
                session.add(project)
                session.commit()
                
                # Update .env with actual dev server port
                from app.agents.developer.src.utils.db_container import update_env_file
                update_env_file(str(workspace_path), dev_port=port)
                
                logger.info(f"Dev server started on port {port} (PID: {process.pid})")
                await broadcast_log(f"Server ready on port {port}", "success")
                
                # Broadcast via WebSocket
                from app.websocket.connection_manager import connection_manager
                await connection_manager.broadcast_to_project({
                    "type": "project_dev_server",
                    "project_id": str(project_id),
                    "running_port": port,
                    "running_pid": process.pid,
                }, project_id)
                
                return {"success": True, "port": port, "pid": process.pid}
            else:
                if process.poll() is not None:
                    raise Exception(f"Process exited with code {process.returncode}")
                else:
                    raise Exception(f"Server started but port {port} not responding after 60s")
                    
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}")
            await broadcast_log(f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}", "warning")
            
            if attempt < max_attempts - 1:
                # Clean up and retry with new port
                await broadcast_log(f"Cleaning up for retry...")
                await asyncio.sleep(0.2)
                
                # Try new port
                port = find_free_port()
                await broadcast_log(f"Retrying with port {port}...")
                logger.info(f"Retrying with port {port}...")
    
    # All attempts failed
    logger.error(f"Failed to start dev server after {max_attempts} attempts: {str(last_error)}")
    await broadcast_log(f"Failed to start dev server after {max_attempts} attempts: {str(last_error)}", "error")
    raise HTTPException(status_code=500, detail=f"Failed to start dev server: {str(last_error)}")


@router.post("/{project_id}/dev-server/stop")
async def stop_project_dev_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID
) -> Any:
    """Stop dev server for project main workspace."""
    
    # Helper: Broadcast log to frontend
    async def broadcast_log(message: str):
        from app.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project({
            "type": "dev_server_log",
            "project_id": str(project_id),
            "message": message,
            "status": "running",
        }, project_id)
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await broadcast_log("Stopping development server...")
    
    # Get workspace path for cleanup
    workspace_path = None
    if project.project_path:
        workspace_path = _get_workspace_path(project.project_path)
    
    # Clean up dev server processes and files
    await broadcast_log("Cleaning up processes...")
    _cleanup_dev_server(
        workspace_path=workspace_path,
        port=project.dev_server_port,
        pid=project.dev_server_pid
    )
    
    # Stop database container if exists (with retry)
    if project.db_container_id:
        await broadcast_log("Stopping database container...")
        try:
            from app.agents.developer.src.utils.db_container import stop_container_by_id, clear_container_from_registry
            
            # Try to stop container (with timeout)
            stopped = stop_container_by_id(project.db_container_id)
            
            if stopped:
                logger.info(f"Stopped database container: {project.db_container_id}")
            else:
                # If stop failed, try force kill
                logger.warning(f"Normal stop failed, trying force kill...")
                try:
                    import docker
                    client = docker.from_env()
                    container = client.containers.get(project.db_container_id)
                    container.kill()  # Force kill
                    container.remove(force=True)
                    logger.info(f"Force killed container: {project.db_container_id}")
                except Exception as e2:
                    logger.error(f"Force kill also failed: {e2}")
            
            # Clear from registry regardless of stop result
            clear_container_from_registry(str(project_id))
            
        except Exception as e:
            logger.warning(f"Failed to stop database container: {e}")
            # Clear from registry anyway to prevent memory leak
            try:
                from app.agents.developer.src.utils.db_container import clear_container_from_registry
                clear_container_from_registry(str(project_id))
            except:
                pass
    
    # Clear from DB
    project.dev_server_port = None
    project.dev_server_pid = None
    project.db_container_id = None
    project.db_port = None
    session.add(project)
    session.commit()
    
    await broadcast_log("Server stopped successfully")
    
    # Broadcast via WebSocket
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "project_dev_server",
        "project_id": str(project_id),
        "running_port": None,
        "running_pid": None,
    }, project_id)
    
    return {"success": True, "message": "Dev server stopped"}


@router.get("/{project_id}/dev-server/status")
def get_project_dev_server_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID
) -> Any:
    """Get dev server status for project."""
    import subprocess
    import sys
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify process is actually running
    is_running = False
    if project.dev_server_port and project.dev_server_pid:
        try:
            import signal
            os.kill(project.dev_server_pid, 0)  # Check if process exists
            is_running = True
        except Exception:
            is_running = False
        
        # If process is dead, clean up DB state
        if not is_running:
            workspace_path = None
            if project.project_path:
                workspace_path = _get_workspace_path(project.project_path)
            _cleanup_dev_server(workspace_path=workspace_path, port=project.dev_server_port, pid=None)
            
            project.dev_server_port = None
            project.dev_server_pid = None
            session.add(project)
            session.commit()
    
    return {
        "running": is_running,
        "port": project.dev_server_port if is_running else None,
        "pid": project.dev_server_pid if is_running else None,
        "has_workspace": bool(project.project_path),
        "db_container_id": project.db_container_id,
        "db_port": project.db_port,
    }


@router.post("/{project_id}/dev-server/restart")
async def restart_project_dev_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID
) -> Any:
    """Restart dev server - stop then start."""
    # Stop first
    await stop_project_dev_server(
        session=session,
        current_user=current_user,
        project_id=project_id
    )
    
    # Brief wait for cleanup
    import asyncio
    await asyncio.sleep(0.1)  # Reduced from 1s
    
    # Start again
    return await start_project_dev_server(
        session=session,
        current_user=current_user,
        project_id=project_id
    )


@router.post("/{project_id}/dev-server/clean")
async def clean_project_dev_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID
) -> Any:
    """Deep clean dev server - remove .next folder and all artifacts."""
    import shutil
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Stop server first
    await stop_project_dev_server(
        session=session,
        current_user=current_user,
        project_id=project_id
    )
    
    # Deep clean workspace
    if project.project_path:
        workspace_path = _get_workspace_path(project.project_path)
        if workspace_path.exists():
            # Remove .next folder completely
            next_dir = workspace_path / ".next"
            if next_dir.exists():
                try:
                    shutil.rmtree(next_dir, ignore_errors=True)
                    logger.info(f"Removed .next directory: {next_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove .next: {e}")
    
    return {"success": True, "message": "Dev server cleaned"}


@router.get("/{project_id}/logs")
async def get_project_logs(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    agent_name: str = Query(None),
    level: str = Query(None),
) -> Any:
    """Get aggregated logs from all stories in project."""
    from app.models import Story, StoryLog
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    story_ids = session.exec(
        select(Story.id).where(Story.project_id == project_id)
    ).all()
    
    if not story_ids:
        return {"logs": [], "total": 0}
    
    stmt = (
        select(StoryLog, Story.title.label("story_title"))
        .join(Story, StoryLog.story_id == Story.id)
        .where(StoryLog.story_id.in_(story_ids))
    )
    
    if level:
        stmt = stmt.where(StoryLog.level == level)
    
    stmt = stmt.order_by(StoryLog.created_at.desc()).limit(limit)
    results = session.exec(stmt).all()
    
    logs = []
    for log, story_title in results:
        logs.append({
            "id": str(log.id),
            "timestamp": log.created_at.isoformat(),
            "agent": log.node or "System",
            "agentRole": log.node or "Agent",
            "type": log.level.value if log.level else "info",
            "action": log.node or "Activity",
            "message": log.content,
            "details": f"Story: {story_title}",
            "story_id": str(log.story_id),
        })
    
    return {"logs": logs, "total": len(logs)}


@router.post("/{project_id}/dev-server/seed")
async def seed_project_database(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID
) -> Any:
    """Manually run database seed for project (same as run_code)."""
    import subprocess
    import sys
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.project_path:
        raise HTTPException(status_code=400, detail="Project has no workspace")
    
    workspace_path = _get_workspace_path(project.project_path)
    if not workspace_path.exists():
        raise HTTPException(status_code=400, detail="Workspace not found")
    
    seed_file = workspace_path / "prisma" / "seed.ts"
    seed_file_js = workspace_path / "prisma" / "seed.js"
    
    if not seed_file.exists() and not seed_file_js.exists():
        raise HTTPException(status_code=400, detail="No seed file found (prisma/seed.ts or prisma/seed.js)")
    
    # Use prisma db seed
    if seed_file.exists():
        seed_args = ["pnpm", "prisma", "db", "seed"]
    else:
        seed_args = ["node", "prisma/seed.js"]
    use_shell = False
    
    # Broadcast start
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "dev_server_log",
        "project_id": str(project_id),
        "message": "Running database seed...",
        "status": "running",
    }, project_id)
    
    try:
        seed_result = await asyncio.to_thread(
            subprocess.run,
            seed_args,
            cwd=str(workspace_path),
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if seed_result.returncode == 0:
            await connection_manager.broadcast_to_project({
                "type": "dev_server_log",
                "project_id": str(project_id),
                "message": "Database seeded successfully",
                "status": "success",
            }, project_id)
            return {"success": True, "message": "Database seeded", "output": seed_result.stdout}
        else:
            error_msg = seed_result.stderr or seed_result.stdout or "Unknown error"
            await connection_manager.broadcast_to_project({
                "type": "dev_server_log",
                "project_id": str(project_id),
                "message": f"Seed failed: {error_msg[:200]}",
                "status": "error",
            }, project_id)
            raise HTTPException(status_code=500, detail=f"Seed failed: {error_msg}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Seed timeout after 120s")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
