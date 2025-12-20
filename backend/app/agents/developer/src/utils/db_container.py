"""Database container management using testcontainers."""
import os
import re
import logging
from typing import Dict, Optional
from uuid import UUID
from testcontainers.postgres import PostgresContainer
from sqlmodel import Session
from app.core.db import engine
from app.models import Story
logger = logging.getLogger(__name__)

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

# Container registry: story_id -> container
_containers: Dict[str, any] = {}


def start_postgres_container(story_id: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, str]:
    """
    Start a postgres container and return connection info.
    Args:
        story_id: Story ID for worktree-specific containers
        project_id: Project ID for main workspace containers
    """
    # Use project_id if provided, otherwise story_id
    container_key = project_id or story_id
    
    container = PostgresContainer("postgres:16")
    container.start()
    
    if container_key:
        _containers[container_key] = container
    
    info = get_connection_info(container_key, container)
    return info


def get_connection_info(story_id: Optional[str] = None, container=None) -> Dict[str, str]:
    """Get connection info"""
    if container is None and story_id:
        container = _containers.get(story_id)
    
    if container is None:
        return {}
    
    container_id = container.get_wrapped_container().id if hasattr(container, 'get_wrapped_container') else ""
    
    return {
        "host": container.get_container_host_ip(),
        "port": str(container.get_exposed_port(5432)),
        "user": container.username,
        "password": container.password,
        "database": container.dbname,
        "container_id": container_id,
    }


def get_database_url(story_id: Optional[str] = None) -> str:
    """Get database URL for a story's container."""
    info = get_connection_info(story_id)
    if not info:
        return ""
    return f"postgresql://{info['user']}:{info['password']}@{info['host']}:{info['port']}/{info['database']}"


def update_env_file(workspace_path: str, story_id: Optional[str] = None, project_id: Optional[str] = None, dev_port: Optional[int] = None) -> bool:
    """Update .env file with database URL and NextAuth config."""
    # Use project_id if provided, otherwise story_id
    container_key = project_id or story_id
    info = get_connection_info(container_key)
    if not info:
        return False
    
    env_path = os.path.join(workspace_path, ".env")
    database_url = f"postgresql://{info['user']}:{info['password']}@{info['host']}:{info['port']}/{info['database']}"
    
    env_content = ""
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    # Update or add DATABASE_URL
    if "DATABASE_URL=" in env_content:
        env_content = re.sub(r'DATABASE_URL=.*', f'DATABASE_URL="{database_url}"', env_content)
    else:
        env_content += f'\nDATABASE_URL="{database_url}"\n'
    
    # Determine app URL (use dev_port if provided, otherwise default to 3000)
    app_url = f"http://localhost:{dev_port}" if dev_port else "http://localhost:3000"
    
    # Update or add NEXT_PUBLIC_APP_URL
    if "NEXT_PUBLIC_APP_URL=" in env_content:
        env_content = re.sub(r'NEXT_PUBLIC_APP_URL=.*', f'NEXT_PUBLIC_APP_URL="{app_url}"', env_content)
    else:
        env_content += f'NEXT_PUBLIC_APP_URL="{app_url}"\n'
    
    # Update or add NEXTAUTH_URL
    if "NEXTAUTH_URL=" in env_content:
        env_content = re.sub(r'NEXTAUTH_URL=.*', f'NEXTAUTH_URL="{app_url}"', env_content)
    else:
        env_content += f'NEXTAUTH_URL="{app_url}"\n'
    
    # Generate or reuse NEXTAUTH_SECRET
    if "NEXTAUTH_SECRET=" not in env_content:
        import secrets
        secret = secrets.token_urlsafe(32)
        env_content += f'NEXTAUTH_SECRET="{secret}"\n'
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    return True


def stop_container(story_id: str) -> bool:
    """Stop and remove container for a story."""
    if story_id not in _containers:
        return False
    
    try:
        container = _containers[story_id]
        container.stop()
        del _containers[story_id]
        return True
    except Exception as e:
        logger.error(f"[db_container] Failed to stop container: {e}")
        return False


def clear_container_from_registry(story_id: str) -> bool:
    if story_id in _containers:
        del _containers[story_id]
        logger.info(f"[db_container] Cleared container from registry: {story_id}")
        return True
    return False


def stop_container_by_id(container_id: str) -> bool:
    """Stop container by docker container ID (for cleanup from DB)."""
    try:
        import docker
        client = docker.from_env()
        
        # Set timeout to avoid hanging
        container = client.containers.get(container_id)
        container.stop(timeout=10)
        container.remove()
        
        # Clear from registry if exists
        for story_id, cont in list(_containers.items()):
            if hasattr(cont, 'id') and cont.id == container_id:
                del _containers[story_id]
                logger.info(f"Cleared container from registry: {story_id}")
                break
        
        return True
    except Exception as e:
        logger.error(f"[db_container] Failed to stop container {container_id}: {e}")
        return False


def update_story_db_info(story_id: str, worktree_path: str, branch_name: str = None) -> bool:
    """Update story in DB with container and workspace info."""
    if not story_id or story_id == "unknown":
        logger.warning(f"[db_container] Invalid story_id: {story_id}")
        return False
    
    info = get_connection_info(story_id)
    
    try:
        
        
        # Validate UUID format
        try:
            story_uuid = UUID(story_id)
        except ValueError:
            logger.error(f"[db_container] Invalid UUID format: {story_id}")
            return False
        
        with Session(engine) as session:
            story = session.get(Story, story_uuid)
            if story:
                story.worktree_path = worktree_path
                if branch_name:
                    story.branch_name = branch_name
                if info:
                    story.db_container_id = info.get("container_id")
                    story.db_port = int(info.get("port", 0))
                session.add(story)
                session.commit()
                logger.info(f"[db_container] Updated story {story_id}: worktree_path={worktree_path}, branch_name={branch_name}")
                return True
            else:
                logger.warning(f"[db_container] Story not found: {story_id}")
    except Exception as e:
        logger.error(f"[db_container] Failed to update story {story_id}: {e}")
    return False
