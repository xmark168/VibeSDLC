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
        from app.api.routes.agent_management import get_available_pool, get_role_class_map
        
        role_class_map = get_role_class_map()
        spawned_count = 0
        
        for agent in created_agents:
            # Get pool for this agent's role (role-specific > universal > any)
            pool_manager = get_available_pool(role_type=agent.role_type)
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
        from app.api.routes.agent_management import get_available_pool
        
        async def terminate_agent(agent: dict):
            pool_manager = get_available_pool(role_type=agent["role_type"])
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
    
    # Check if path exists
    workspace_path = Path(project.project_path)
    if not workspace_path.exists():
        raise HTTPException(status_code=400, detail="Project workspace not found")
    
    is_windows = sys.platform == 'win32'
    
    # Helper: Find free port
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    # Helper: Kill process on port
    def kill_process_on_port(port: int) -> bool:
        try:
            if is_windows:
                result = subprocess.run(
                    f'netstat -ano | findstr :{port}',
                    shell=True, capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = int(parts[-1])
                        subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, capture_output=True)
                        return True
            else:
                result = subprocess.run(
                    f'lsof -ti:{port}',
                    shell=True, capture_output=True, text=True
                )
                if result.stdout.strip():
                    pid = int(result.stdout.strip())
                    os.kill(pid, 9)
                    return True
        except Exception:
            pass
        return False
    
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
                await asyncio.sleep(0.5)
        return False
    
    # Kill existing process if running
    if project.dev_server_port:
        kill_process_on_port(project.dev_server_port)
        await asyncio.sleep(0.5)
    
    # Check if node_modules exists, if not run pnpm install
    node_modules_path = workspace_path / "node_modules"
    if not node_modules_path.exists():
        logger.info(f"node_modules not found, running pnpm install...")
        # Run in thread to avoid blocking event loop (can take 5+ minutes)
        install_result = await asyncio.to_thread(
            subprocess.run,
            "pnpm install" if is_windows else ["pnpm", "install"],
            cwd=str(workspace_path),
            shell=is_windows,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout for install
        )
        if install_result.returncode != 0:
            logger.error(f"pnpm install failed: {install_result.stderr}")
            raise HTTPException(status_code=500, detail=f"Failed to install dependencies: {install_result.stderr[:500]}")
        logger.info("pnpm install completed")
    
    port = find_free_port()
    logger.info(f"Starting dev server for project {project_id} on port {port}")
    
    try:
        logger.info(f"Workspace path: {workspace_path}")
        process = subprocess.Popen(
            f"pnpm dev --port {port}" if is_windows else ["pnpm", "dev", "--port", str(port)],
            cwd=str(workspace_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=is_windows,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if is_windows else 0,
            env={**os.environ, "FORCE_COLOR": "0"},
        )
        
        # Wait for server to be ready
        if await wait_for_port_async(port, timeout=15.0) and process.poll() is None:
            # Store in project
            project.dev_server_port = port
            project.dev_server_pid = process.pid
            session.add(project)
            session.commit()
            
            logger.info(f"Dev server started on port {port} (PID: {process.pid})")
            
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
                stdout, stderr = process.communicate()
                logger.error(f"Process stdout: {stdout.decode() if stdout else ''}")
                logger.error(f"Process stderr: {stderr.decode() if stderr else ''}")
                raise Exception(f"Process exited with code {process.returncode}")
            raise Exception("Server did not start in time")
            
    except Exception as e:
        logger.error(f"Failed to start dev server: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start dev server: {str(e)}")


@router.post("/{project_id}/dev-server/stop")
async def stop_project_dev_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID
) -> Any:
    """Stop dev server for project main workspace."""
    import subprocess
    import sys
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    is_windows = sys.platform == 'win32'
    
    # Kill by PID
    if project.dev_server_pid:
        try:
            if is_windows:
                subprocess.run(f"taskkill /F /PID {project.dev_server_pid} /T", shell=True, capture_output=True)
            else:
                os.kill(project.dev_server_pid, 9)
        except Exception as e:
            logger.warning(f"Failed to kill process {project.dev_server_pid}: {e}")
    
    # Kill by port
    if project.dev_server_port:
        try:
            if is_windows:
                result = subprocess.run(
                    f'netstat -ano | findstr :{project.dev_server_port}',
                    shell=True, capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = int(parts[-1])
                        subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, capture_output=True)
            else:
                result = subprocess.run(
                    f'lsof -ti:{project.dev_server_port}',
                    shell=True, capture_output=True, text=True
                )
                if result.stdout.strip():
                    pid = int(result.stdout.strip())
                    os.kill(pid, 9)
        except Exception:
            pass
    
    # Clear from DB
    project.dev_server_port = None
    project.dev_server_pid = None
    session.add(project)
    session.commit()
    
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
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "running": bool(project.dev_server_port),
        "port": project.dev_server_port,
        "pid": project.dev_server_pid,
        "has_workspace": bool(project.project_path),
    }
