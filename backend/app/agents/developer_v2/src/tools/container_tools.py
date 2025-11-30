"""Container Tools for Persistent Dev Environments.

Provides LLM-callable tools for managing Docker containers per branch.
Each branch gets its own isolated dev environment (App + DB) via docker-compose.

Speed optimizations:
- Uses docker-compose for reliable container orchestration
- tmpfs for DB (no disk I/O)
- Health checks ensure DB is ready before app starts
- Subprocess calls instead of Docker SDK (faster)
"""

import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
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
    """Manage persistent dev containers per branch using docker-compose.
    
    Features:
    - One container set per branch (App + PostgreSQL)
    - Fast startup with docker-compose
    - tmpfs for DB (speed)
    - Health checks ensure DB ready
    - Subprocess for fast exec
    """
    
    def __init__(self):
        self._compose_file = None
        self._containers = {}
    
    def _get_compose_file(self) -> str:
        """Get path to docker-compose.dev.yml."""
        if self._compose_file is None:
            # Find compose file relative to this module
            module_dir = Path(__file__).parent.parent.parent  # developer_v2/
            compose_path = module_dir / "docker" / "docker-compose.dev.yml"
            
            if not compose_path.exists():
                raise FileNotFoundError(f"docker-compose.dev.yml not found at {compose_path}")
            
            self._compose_file = str(compose_path)
        
        return self._compose_file
    
    def _safe_name(self, branch_name: str) -> str:
        """Convert branch name to safe container name."""
        return re.sub(r'[^a-zA-Z0-9]', '-', branch_name)[:50].lower()
    
    def _get_container_prefix(self, branch_name: str) -> str:
        """Generate container prefix for branch."""
        return f"dev-{self._safe_name(branch_name)}"
    
    def _get_app_container_name(self, branch_name: str) -> str:
        """Get app container name."""
        return f"{self._get_container_prefix(branch_name)}-app"
    
    def _get_db_container_name(self, branch_name: str) -> str:
        """Get DB container name."""
        return f"{self._get_container_prefix(branch_name)}-db"
    
    def _get_image(self, project_type: str) -> str:
        """Get Docker image for project type."""
        image_map = {
            "node": "node:20-slim",
            "python": "python:3.11-slim",
            "rust": "rust:1.75-slim",
            "go": "golang:1.21-alpine",
        }
        return image_map.get(project_type, "node:20-slim")
    
    def _is_running(self, branch_name: str) -> bool:
        """Check if containers are running."""
        app_name = self._get_app_container_name(branch_name)
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", app_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and "true" in result.stdout.lower()
        except Exception:
            return False
    
    def _run_compose(self, branch_name: str, workspace_path: str, project_type: str, command: list) -> subprocess.CompletedProcess:
        """Run docker-compose command with environment."""
        compose_file = self._get_compose_file()
        prefix = self._get_container_prefix(branch_name)
        
        env = {
            **os.environ,
            "CONTAINER_PREFIX": prefix,
            "WORKSPACE_PATH": workspace_path,
            "APP_IMAGE": self._get_image(project_type),
        }
        
        full_cmd = ["docker-compose", "-f", compose_file, "-p", prefix] + command
        
        return subprocess.run(
            full_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    
    def get_or_create(self, branch_name: str, workspace_path: str, project_type: str = "node") -> dict:
        """Get existing or create new dev container using docker-compose.
        
        Args:
            branch_name: Git branch name (used as container identifier)
            workspace_path: Path to workspace to mount
            project_type: Project type (node, python, etc.)
            
        Returns:
            Container info dict with name, status, db_url, etc.
        """
        app_name = self._get_app_container_name(branch_name)
        db_name = self._get_db_container_name(branch_name)
        
        # Check if already running
        if self._is_running(branch_name):
            logger.info(f"[DevContainerManager] Reusing running container: {app_name}")
            return self._get_container_info(branch_name)
        
        logger.info(f"[DevContainerManager] Starting dev environment for {branch_name}...")
        
        # Start with docker-compose
        result = self._run_compose(branch_name, workspace_path, project_type, ["up", "-d", "--wait"])
        
        if result.returncode != 0:
            logger.error(f"[DevContainerManager] docker-compose up failed: {result.stderr}")
            # Try without --wait (older docker-compose)
            result = self._run_compose(branch_name, workspace_path, project_type, ["up", "-d"])
            
            if result.returncode != 0:
                raise RuntimeError(f"docker-compose up failed: {result.stderr}")
            
            # Manual wait for DB
            self._wait_for_db(branch_name, timeout=30)
        
        logger.info(f"[DevContainerManager] Started: {app_name}")
        
        # Install bun/pnpm in node containers (one-time setup)
        if project_type == "node":
            self._setup_node_tools(branch_name)
        
        return self._get_container_info(branch_name)
    
    def _setup_node_tools(self, branch_name: str):
        """Install bun and pnpm in node container (if not already installed)."""
        app_name = self._get_app_container_name(branch_name)
        
        # Check if bun already installed
        check = subprocess.run(
            ["docker", "exec", app_name, "which", "bun"],
            capture_output=True,
            timeout=10,
        )
        
        if check.returncode == 0:
            logger.info("[DevContainerManager] bun already installed")
            return
        
        logger.info("[DevContainerManager] Installing bun and pnpm...")
        
        # Install bun and pnpm
        subprocess.run(
            ["docker", "exec", app_name, "npm", "install", "-g", "bun", "pnpm"],
            capture_output=True,
            timeout=120,
        )
    
    def _wait_for_db(self, branch_name: str, timeout: int = 30) -> bool:
        """Wait for PostgreSQL to be ready."""
        db_name = self._get_db_container_name(branch_name)
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                result = subprocess.run(
                    ["docker", "exec", db_name, "pg_isready", "-U", "dev", "-d", "app"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    logger.info("[DevContainerManager] DB is ready")
                    return True
            except Exception:
                pass
            time.sleep(1)
        
        logger.warning("[DevContainerManager] DB might not be ready (timeout)")
        return False
    
    def _get_container_info(self, branch_name: str) -> dict:
        """Get container info dict."""
        app_name = self._get_app_container_name(branch_name)
        db_name = self._get_db_container_name(branch_name)
        
        # Get status
        status = "unknown"
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", app_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                status = result.stdout.strip()
        except Exception:
            pass
        
        return {
            "name": app_name,
            "status": status,
            "branch": branch_name,
            "db_container": db_name,
            "db_url": f"postgresql://dev:dev@{db_name}:5432/app",
        }
    
    def exec(self, branch_name: str, command: str, workdir: str = "/app") -> dict:
        """Execute command in app container using subprocess (fast).
        
        Args:
            branch_name: Branch name to identify container
            command: Shell command to execute
            workdir: Working directory inside container
            
        Returns:
            Dict with exit_code and output
        """
        app_name = self._get_app_container_name(branch_name)
        
        try:
            # Always use bash -c for reliable command execution
            full_cmd = [
                "docker", "exec",
                "-w", workdir,
                app_name,
                "bash", "-c", command
            ]
            
            logger.info(f"[DevContainerManager] Exec: {command[:80]}...")
            
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            output = result.stdout + result.stderr
            
            logger.info(f"[DevContainerManager] Exit code: {result.returncode}")
            
            return {
                "exit_code": result.returncode,
                "output": output,
                "command": command,
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"[DevContainerManager] Command timeout: {command}")
            return {
                "exit_code": -1,
                "output": f"Error: Command timed out after 300s",
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
        """Stop containers (preserve for later restart)."""
        prefix = self._get_container_prefix(branch_name)
        
        try:
            compose_file = self._get_compose_file()
            subprocess.run(
                ["docker-compose", "-f", compose_file, "-p", prefix, "stop"],
                capture_output=True,
                timeout=30,
            )
            logger.info(f"[DevContainerManager] Stopped: {prefix}")
        except Exception as e:
            logger.debug(f"[DevContainerManager] Stop error: {e}")
    
    def remove(self, branch_name: str):
        """Remove containers completely."""
        prefix = self._get_container_prefix(branch_name)
        
        try:
            compose_file = self._get_compose_file()
            subprocess.run(
                ["docker-compose", "-f", compose_file, "-p", prefix, "down", "-v", "--remove-orphans"],
                capture_output=True,
                timeout=60,
            )
            logger.info(f"[DevContainerManager] Removed: {prefix}")
        except Exception as e:
            logger.warning(f"[DevContainerManager] Remove error: {e}")
        
        self._containers.pop(branch_name, None)
    
    def get_logs(self, branch_name: str, tail: int = 100) -> str:
        """Get logs from app container."""
        app_name = self._get_app_container_name(branch_name)
        
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(tail), app_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error getting logs: {str(e)}"
    
    def status(self, branch_name: str) -> dict:
        """Get status of dev environment."""
        app_name = self._get_app_container_name(branch_name)
        db_name = self._get_db_container_name(branch_name)
        
        result = {
            "branch": branch_name,
            "app": {"name": app_name, "status": "not_found"},
            "db": {"name": db_name, "status": "not_found"},
        }
        
        for key, name in [("app", app_name), ("db", db_name)]:
            try:
                inspect = subprocess.run(
                    ["docker", "inspect", "-f", "{{.State.Status}}", name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if inspect.returncode == 0:
                    result[key]["status"] = inspect.stdout.strip()
            except Exception:
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
    - bun install, bun test
    - pnpm install, pnpm test
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
        return f"Container stopped: {branch_name}"
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
