"""Container Tools for Persistent Dev Environments.

Provides LLM-callable tools for managing Docker containers per branch.
Each branch gets its own isolated dev environment (App + DB).
"""

import json
import logging
import re
import time
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Global container context
_container_context = {
    "branch_name": None,
    "container_name": None,
    "workspace_path": None,
}


def set_container_context(branch_name: str = None, container_name: str = None, workspace_path: str = None):
    """Set global context for container tools."""
    if branch_name:
        _container_context["branch_name"] = branch_name
    if container_name:
        _container_context["container_name"] = container_name
    if workspace_path:
        _container_context["workspace_path"] = workspace_path


class DevContainerManager:
    """Manage persistent dev containers per branch.
    
    Features:
    - One container per branch (App + PostgreSQL)
    - Reuse existing containers (fast!)
    - Stop instead of remove (preserve data)
    - LLM can exec commands via tools
    """
    
    def __init__(self):
        self._client = None
        self._containers = {}  # branch -> container_info
    
    @property
    def client(self):
        """Lazy load Docker client."""
        if self._client is None:
            try:
                import docker
                self._client = docker.from_env()
            except Exception as e:
                logger.error(f"[DevContainerManager] Failed to connect to Docker: {e}")
                raise
        return self._client
    
    def _safe_name(self, branch_name: str) -> str:
        """Convert branch name to safe container name."""
        return re.sub(r'[^a-zA-Z0-9]', '-', branch_name)[:50]
    
    def _get_container_name(self, branch_name: str) -> str:
        """Generate container name for branch."""
        return f"dev-env-{self._safe_name(branch_name)}"
    
    def _get_network_name(self, branch_name: str) -> str:
        """Generate network name for branch."""
        return f"dev-net-{self._safe_name(branch_name)}"
    
    def _get_db_container_name(self, branch_name: str) -> str:
        """Generate DB container name for branch."""
        return f"dev-db-{self._safe_name(branch_name)}"
    
    def _wait_for_db(self, db_container, timeout: int = 30) -> bool:
        """Wait for PostgreSQL to be ready."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                exit_code, _ = db_container.exec_run("pg_isready -U dev -d app")
                if exit_code == 0:
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False
    
    def get_or_create(self, branch_name: str, workspace_path: str, project_type: str = "node") -> dict:
        """Get existing or create new dev container.
        
        Args:
            branch_name: Git branch name (used as container identifier)
            workspace_path: Path to workspace to mount
            project_type: Project type (node, python, etc.)
            
        Returns:
            Container info dict with name, status, db_url, etc.
        """
        import docker
        
        app_container_name = self._get_container_name(branch_name)
        db_container_name = self._get_db_container_name(branch_name)
        network_name = self._get_network_name(branch_name)
        
        try:
            # Check if app container exists
            app_container = self.client.containers.get(app_container_name)
            
            if app_container.status == "exited":
                # Also start DB container if exists
                try:
                    db_container = self.client.containers.get(db_container_name)
                    if db_container.status == "exited":
                        db_container.start()
                        self._wait_for_db(db_container)
                except docker.errors.NotFound:
                    pass
                
                app_container.start()
                logger.info(f"[DevContainerManager] Restarted: {app_container_name}")
            
            return self._get_container_info(branch_name, app_container)
            
        except docker.errors.NotFound:
            # Create new containers
            return self._create_containers(branch_name, workspace_path, project_type)
    
    def _create_containers(self, branch_name: str, workspace_path: str, project_type: str) -> dict:
        """Create new dev environment (App + DB containers)."""
        import docker
        
        app_container_name = self._get_container_name(branch_name)
        db_container_name = self._get_db_container_name(branch_name)
        network_name = self._get_network_name(branch_name)
        
        logger.info(f"[DevContainerManager] Creating dev environment for {branch_name}...")
        
        # Create network
        try:
            network = self.client.networks.get(network_name)
        except docker.errors.NotFound:
            network = self.client.networks.create(network_name, driver="bridge")
            logger.info(f"[DevContainerManager] Created network: {network_name}")
        
        # Create DB container
        try:
            db_container = self.client.containers.get(db_container_name)
            if db_container.status == "exited":
                db_container.start()
        except docker.errors.NotFound:
            db_container = self.client.containers.run(
                "postgres:16-alpine",
                name=db_container_name,
                environment={
                    "POSTGRES_USER": "dev",
                    "POSTGRES_PASSWORD": "dev",
                    "POSTGRES_DB": "app",
                },
                network=network_name,
                detach=True,
                remove=False,
            )
            logger.info(f"[DevContainerManager] Created DB container: {db_container_name}")
        
        # Wait for DB to be ready
        if not self._wait_for_db(db_container):
            logger.warning("[DevContainerManager] DB might not be ready")
        
        # Select base image based on project type
        image_map = {
            "node": "node:20-slim",
            "python": "python:3.11-slim",
            "rust": "rust:1.75-slim",
            "go": "golang:1.21-alpine",
        }
        base_image = image_map.get(project_type, "node:20-slim")
        
        # Create App container
        app_container = self.client.containers.run(
            base_image,
            name=app_container_name,
            working_dir="/app",
            volumes={
                workspace_path: {"bind": "/app", "mode": "rw"},
            },
            environment={
                "DATABASE_URL": f"postgresql://dev:dev@{db_container_name}:5432/app",
                "NODE_ENV": "development",
            },
            network=network_name,
            command="tail -f /dev/null",  # Keep container running
            detach=True,
            remove=False,
        )
        logger.info(f"[DevContainerManager] Created app container: {app_container_name}")
        
        # Cache container info
        info = self._get_container_info(branch_name, app_container)
        self._containers[branch_name] = info
        
        return info
    
    def _get_container_info(self, branch_name: str, container) -> dict:
        """Get container info dict."""
        db_container_name = self._get_db_container_name(branch_name)
        
        return {
            "name": container.name,
            "id": container.id[:12],
            "status": container.status,
            "branch": branch_name,
            "db_container": db_container_name,
            "db_url": f"postgresql://dev:dev@{db_container_name}:5432/app",
        }
    
    def exec(self, branch_name: str, command: str, workdir: str = "/app") -> dict:
        """Execute command in app container.
        
        Args:
            branch_name: Branch name to identify container
            command: Shell command to execute
            workdir: Working directory inside container
            
        Returns:
            Dict with exit_code and output
        """
        app_container_name = self._get_container_name(branch_name)
        
        try:
            container = self.client.containers.get(app_container_name)
            
            if container.status != "running":
                container.start()
                time.sleep(1)
            
            exit_code, output = container.exec_run(
                f"sh -c '{command}'",
                workdir=workdir,
            )
            
            output_str = output.decode("utf-8", errors="replace") if output else ""
            
            logger.info(f"[DevContainerManager] Exec '{command[:50]}...' -> exit={exit_code}")
            
            return {
                "exit_code": exit_code,
                "output": output_str,
                "command": command,
            }
            
        except Exception as e:
            logger.error(f"[DevContainerManager] Exec error: {e}")
            return {
                "exit_code": -1,
                "output": f"Error: {str(e)}",
                "command": command,
            }
    
    def stop(self, branch_name: str):
        """Stop containers (preserve data for later)."""
        app_container_name = self._get_container_name(branch_name)
        db_container_name = self._get_db_container_name(branch_name)
        
        for name in [app_container_name, db_container_name]:
            try:
                container = self.client.containers.get(name)
                container.stop(timeout=10)
                logger.info(f"[DevContainerManager] Stopped: {name}")
            except Exception as e:
                logger.debug(f"[DevContainerManager] Stop {name}: {e}")
    
    def remove(self, branch_name: str):
        """Remove containers completely."""
        import docker
        
        app_container_name = self._get_container_name(branch_name)
        db_container_name = self._get_db_container_name(branch_name)
        network_name = self._get_network_name(branch_name)
        
        # Remove containers
        for name in [app_container_name, db_container_name]:
            try:
                container = self.client.containers.get(name)
                container.remove(force=True, v=True)
                logger.info(f"[DevContainerManager] Removed: {name}")
            except docker.errors.NotFound:
                pass
            except Exception as e:
                logger.warning(f"[DevContainerManager] Remove {name}: {e}")
        
        # Remove network
        try:
            network = self.client.networks.get(network_name)
            network.remove()
            logger.info(f"[DevContainerManager] Removed network: {network_name}")
        except Exception:
            pass
        
        # Clear cache
        self._containers.pop(branch_name, None)
    
    def get_logs(self, branch_name: str, tail: int = 100) -> str:
        """Get logs from app container."""
        app_container_name = self._get_container_name(branch_name)
        
        try:
            container = self.client.containers.get(app_container_name)
            return container.logs(tail=tail).decode("utf-8", errors="replace")
        except Exception as e:
            return f"Error getting logs: {str(e)}"
    
    def status(self, branch_name: str) -> dict:
        """Get status of dev environment."""
        import docker
        
        app_container_name = self._get_container_name(branch_name)
        db_container_name = self._get_db_container_name(branch_name)
        
        result = {
            "branch": branch_name,
            "app": {"name": app_container_name, "status": "not_found"},
            "db": {"name": db_container_name, "status": "not_found"},
        }
        
        for key, name in [("app", app_container_name), ("db", db_container_name)]:
            try:
                container = self.client.containers.get(name)
                result[key]["status"] = container.status
                result[key]["id"] = container.id[:12]
            except docker.errors.NotFound:
                pass
        
        return result


# Global instance
dev_container_manager = DevContainerManager()


# =============================================================================
# LLM Tools
# =============================================================================

@tool
def container_exec(command: str) -> str:
    """Execute a shell command inside the dev container.
    
    Use this to run commands like:
    - npm install, npm test, npm run build
    - npx prisma generate, npx prisma db push
    - python -m pytest, pip install
    
    Args:
        command: Shell command to execute (e.g., 'npm test', 'npx prisma db push')
    
    Returns:
        Command output with exit code
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No container context set. Call container_start first."
    
    result = dev_container_manager.exec(branch_name, command)
    
    output = result.get("output", "")
    exit_code = result.get("exit_code", -1)
    
    return f"Exit code: {exit_code}\n\n{output}"


@tool
def container_logs(tail: int = 100) -> str:
    """Get recent logs from the dev container.
    
    Useful for debugging when commands fail or to see application output.
    
    Args:
        tail: Number of log lines to return (default: 100)
    
    Returns:
        Container logs
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No container context set."
    
    return dev_container_manager.get_logs(branch_name, tail)


@tool
def container_status() -> str:
    """Get status of the dev environment (app + db containers).
    
    Returns:
        JSON with container status information
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No container context set."
    
    status = dev_container_manager.status(branch_name)
    return json.dumps(status, indent=2)


@tool
def container_start(workspace_path: str, project_type: str = "node") -> str:
    """Start or create the dev container for current branch.
    
    This will:
    - Create a new container if none exists
    - Start an existing stopped container
    - Return container info with DATABASE_URL
    
    Args:
        workspace_path: Path to the project workspace
        project_type: Type of project (node, python, rust, go)
    
    Returns:
        JSON with container info
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No branch context set."
    
    try:
        info = dev_container_manager.get_or_create(branch_name, workspace_path, project_type)
        return json.dumps(info, indent=2)
    except Exception as e:
        return f"Error starting container: {str(e)}"


@tool
def container_stop() -> str:
    """Stop the dev container (preserves data for later).
    
    Use this when done with the task. Container can be restarted later
    without losing installed dependencies or database data.
    
    Returns:
        Confirmation message
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No container context set."
    
    try:
        dev_container_manager.stop(branch_name)
        return f"Container stopped: dev-env-{branch_name}"
    except Exception as e:
        return f"Error stopping container: {str(e)}"


def get_container_tools() -> list:
    """Get all container tools for LLM."""
    return [
        container_exec,
        container_logs,
        container_status,
        container_start,
        container_stop,
    ]
