"""Container Tools for Persistent Dev Environments.

Provides LLM-callable tools for managing Docker containers per branch.
Each branch gets its own isolated PostgreSQL database via docker-compose.
App runs directly on host for faster execution.

Architecture:
- Only PostgreSQL runs in Docker (isolated per branch)
- App runs directly on host (faster installs, native file access)
- DB port auto-selected if default (5432) is occupied
"""

import json
import logging
import os
import re
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def find_available_port(start_port: int = 3000, max_attempts: int = 100) -> int:
    """Find an available port on the host machine.
    
    Args:
        start_port: Port to start searching from
        max_attempts: Maximum number of ports to try
        
    Returns:
        Available port number
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts}")

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
    """Manage PostgreSQL containers per branch, execute commands on host.
    
    Features:
    - One PostgreSQL container per branch (isolated DB)
    - App runs directly on host (not in container)
    - Dynamic DB port mapping (auto-select if 5432 occupied)
    - Commands execute on host with DATABASE_URL env var
    """
    
    def __init__(self):
        self._compose_file = None
        self._containers = {}
        self._branch_db_ports = {}  # Cache: branch_name -> db_port
    
    def _get_compose_file(self, workspace_path: str = None) -> str:
        """Get path to docker-compose.dev.yml.
        
        Priority:
        1. Workspace's docker-compose.dev.yml (if exists and valid)
        2. Default from developer_v2/docker/
        
        Auto-fixes outdated workspace configs (old bun install && bun run dev command).
        """
        # Check workspace first
        if workspace_path:
            workspace_compose = Path(workspace_path) / "docker-compose.dev.yml"
            if workspace_compose.exists():
                # Auto-fix outdated config
                self._fix_outdated_compose(workspace_compose)
                return str(workspace_compose)
        
        # Fallback to default
        if self._compose_file is None:
            module_dir = Path(__file__).parent.parent.parent  # developer_v2/
            compose_path = module_dir / "docker" / "docker-compose.dev.yml"
            
            if not compose_path.exists():
                raise FileNotFoundError(f"docker-compose.dev.yml not found at {compose_path}")
            
            self._compose_file = str(compose_path)
        
        return self._compose_file
    
    def _fix_outdated_compose(self, compose_path: Path):
        """Fix outdated docker-compose.dev.yml with old bun install command."""
        try:
            content = compose_path.read_text(encoding='utf-8')
            # Check for old command pattern
            if 'bun install && bun run dev' in content:
                logger.info(f"[DevContainerManager] Fixing outdated compose: {compose_path}")
                new_content = content.replace(
                    '["sh", "-c", "bun install && bun run dev"]',
                    '["tail", "-f", "/dev/null"]'
                )
                compose_path.write_text(new_content, encoding='utf-8')
                logger.info("[DevContainerManager] Fixed: command -> tail -f /dev/null")
        except Exception as e:
            logger.warning(f"[DevContainerManager] Could not fix compose: {e}")
    
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
            "node": "oven/bun:1",  # bun pre-installed, faster than node:20-slim
            "python": "python:3.11-slim",
            "rust": "rust:1.75-slim",
            "go": "golang:1.21-alpine",
        }
        return image_map.get(project_type, "oven/bun:1")
    
    def _is_db_running(self, branch_name: str) -> bool:
        """Check if DB container is running."""
        db_name = self._get_db_container_name(branch_name)
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", db_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and "true" in result.stdout.lower()
        except Exception:
            return False
    
    def _get_or_assign_db_port(self, branch_name: str) -> int:
        """Get cached DB port or find a new available port for branch."""
        # Check cache first
        if branch_name in self._branch_db_ports:
            return self._branch_db_ports[branch_name]
        
        # Check if container already has a port mapped
        existing_port = self._get_db_container_port(branch_name)
        if existing_port:
            self._branch_db_ports[branch_name] = existing_port
            return existing_port
        
        # Find new available port starting from 5432
        port = find_available_port(start_port=5432)
        self._branch_db_ports[branch_name] = port
        logger.info(f"[DevContainerManager] Assigned DB port {port} to branch {branch_name}")
        return port
    
    def _get_db_container_port(self, branch_name: str) -> Optional[int]:
        """Get the host port mapped to container's port 5432."""
        db_name = self._get_db_container_name(branch_name)
        try:
            result = subprocess.run(
                ["docker", "port", db_name, "5432"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Output format: "0.0.0.0:5432" or ":::5432"
                port_str = result.stdout.strip().split(':')[-1]
                return int(port_str)
        except Exception:
            pass
        return None
    
    def _run_compose(self, branch_name: str, workspace_path: str, command: list) -> subprocess.CompletedProcess:
        """Run docker-compose command with environment."""
        compose_file = self._get_compose_file(workspace_path)
        logger.info(f"[DevContainerManager] Using compose file: {compose_file}")
        prefix = self._get_container_prefix(branch_name)
        db_port = self._get_or_assign_db_port(branch_name)
        
        env = {
            **os.environ,
            "COMPOSE_PROJECT_NAME": prefix,
            "DB_PORT": str(db_port),
        }
        
        full_cmd = ["docker-compose", "-f", compose_file, "-p", prefix] + command
        
        return subprocess.run(
            full_cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120,
        )
    
    def get_or_create(self, branch_name: str, workspace_path: str, project_type: str = "node") -> dict:
        """Start PostgreSQL container for branch, app runs on host.
        
        Args:
            branch_name: Git branch name (used as container identifier)
            workspace_path: Path to workspace (stored for exec commands)
            project_type: Project type (unused, kept for compatibility)
            
        Returns:
            Container info dict with db_port, db_url (host-accessible), etc.
        """
        db_name = self._get_db_container_name(branch_name)
        
        # Store workspace path for exec commands
        _container_context["workspace_path"] = workspace_path
        
        # Check if DB already running
        if self._is_db_running(branch_name):
            logger.info(f"[DevContainerManager] Reusing running DB: {db_name}")
            return self._get_container_info(branch_name)
        
        logger.info(f"[DevContainerManager] Starting PostgreSQL for {branch_name}...")
        
        # Start only DB service with docker-compose
        result = self._run_compose(branch_name, workspace_path, ["up", "-d", "--wait", "db"])
        
        if result.returncode != 0:
            logger.error(f"[DevContainerManager] docker-compose up failed: {result.stderr}")
            # Try without --wait (older docker-compose)
            result = self._run_compose(branch_name, workspace_path, ["up", "-d", "db"])
            
            if result.returncode != 0:
                raise RuntimeError(f"docker-compose up failed: {result.stderr}")
            
            # Manual wait for DB
            self._wait_for_db(branch_name, timeout=30)
        
        logger.info(f"[DevContainerManager] DB started: {db_name}")
        
        return self._get_container_info(branch_name)
    
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
        """Get container info dict with host-accessible DB URL."""
        db_name = self._get_db_container_name(branch_name)
        
        # Get DB status
        status = "unknown"
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", db_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                status = result.stdout.strip()
        except Exception:
            pass
        
        # Get DB host port
        db_port = self._get_db_container_port(branch_name) or self._branch_db_ports.get(branch_name, 5432)
        
        return {
            "db_container": db_name,
            "db_status": status,
            "branch": branch_name,
            "db_port": db_port,
            "db_url": f"postgresql://dev:dev@localhost:{db_port}/app",
        }
    
    def exec(self, branch_name: str, command: str, workdir: str = None, timeout: int = 120) -> dict:
        """Execute command directly on HOST with DATABASE_URL env var.
        
        Args:
            branch_name: Branch name to get DB port
            command: Shell command to execute
            workdir: Working directory (defaults to workspace_path from context)
            timeout: Command timeout in seconds (default 120s)
            
        Returns:
            Dict with exit_code and output
        """
        workspace_path = workdir or _container_context.get("workspace_path")
        db_port = self._branch_db_ports.get(branch_name, 5432)
        
        try:
            # Set up environment with DATABASE_URL pointing to localhost
            env = os.environ.copy()
            env["DATABASE_URL"] = f"postgresql://dev:dev@localhost:{db_port}/app"
            env["CI"] = "1"
            env["BUN_NO_UPDATE_NOTIFIER"] = "1"
            
            logger.info(f"[DevContainerManager] Exec on host: {command[:80]}...")
            
            # Execute on host
            if os.name == "nt":  # Windows
                shell_cmd = ["cmd", "/c", command]
                use_shell = False
            else:
                shell_cmd = command
                use_shell = True
            
            result = subprocess.run(
                shell_cmd,
                shell=use_shell,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                env=env,
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
                "output": f"Error: Command timed out after {timeout}s",
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
        """Stop DB container (preserve for later restart)."""
        prefix = self._get_container_prefix(branch_name)
        
        try:
            compose_file = self._get_compose_file()
            subprocess.run(
                ["docker-compose", "-f", compose_file, "-p", prefix, "stop"],
                capture_output=True,
                timeout=30,
            )
            logger.info(f"[DevContainerManager] Stopped DB: {prefix}")
        except Exception as e:
            logger.debug(f"[DevContainerManager] Stop error: {e}")
    
    def remove(self, branch_name: str):
        """Remove DB container completely."""
        prefix = self._get_container_prefix(branch_name)
        
        try:
            compose_file = self._get_compose_file()
            subprocess.run(
                ["docker-compose", "-f", compose_file, "-p", prefix, "down", "-v", "--remove-orphans"],
                capture_output=True,
                timeout=60,
            )
            logger.info(f"[DevContainerManager] Removed DB: {prefix}")
        except Exception as e:
            logger.warning(f"[DevContainerManager] Remove error: {e}")
        
        self._containers.pop(branch_name, None)
        self._branch_db_ports.pop(branch_name, None)
    
    def get_logs(self, branch_name: str, tail: int = 100) -> str:
        """Get logs from DB container."""
        db_name = self._get_db_container_name(branch_name)
        
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(tail), db_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error getting logs: {str(e)}"
    
    def status(self, branch_name: str) -> dict:
        """Get status of DB container."""
        db_name = self._get_db_container_name(branch_name)
        db_port = self._branch_db_ports.get(branch_name, 5432)
        
        result = {
            "branch": branch_name,
            "db": {"name": db_name, "status": "not_found", "port": db_port},
        }
        
        try:
            inspect = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", db_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if inspect.returncode == 0:
                result["db"]["status"] = inspect.stdout.strip()
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
    """Execute a shell command on HOST with DATABASE_URL set.
    
    Use this to run commands like:
    - bun install, bun test, bun run build
    - bunx prisma generate, bunx prisma db push
    - npm install, npm test
    - python -m pytest, pip install
    
    DATABASE_URL is automatically set to connect to the PostgreSQL container.
    
    Args:
        command: Shell command to execute (e.g., 'bun test', 'bunx prisma db push')
    
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
    """Get recent logs from the PostgreSQL container.
    
    Useful for debugging database issues.
    
    Args:
        tail: Number of log lines to return (default: 100)
    
    Returns:
        Database container logs
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No container context set."
    
    return dev_container_manager.get_logs(branch_name, tail)


@tool
def container_status() -> str:
    """Get status of the PostgreSQL container.
    
    Returns:
        JSON with DB container status and port
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No container context set."
    
    status = dev_container_manager.status(branch_name)
    return json.dumps(status, indent=2)


@tool
def container_start(workspace_path: str, project_type: str = "node") -> str:
    """Start PostgreSQL container for current branch.
    
    This will:
    - Start PostgreSQL in Docker (isolated per branch)
    - Auto-select port if 5432 is occupied
    - Return DATABASE_URL for host connection
    
    App runs directly on host, not in container.
    
    Args:
        workspace_path: Path to the project workspace
        project_type: Type of project (unused, kept for compatibility)
    
    Returns:
        JSON with db_port, db_url
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No branch context set."
    
    try:
        info = dev_container_manager.get_or_create(branch_name, workspace_path, project_type)
        return json.dumps(info, indent=2)
    except Exception as e:
        return f"Error starting DB container: {str(e)}"


@tool
def container_stop() -> str:
    """Stop the PostgreSQL container (preserves data for later).
    
    Use this when done with the task. Container can be restarted later
    without losing database data.
    
    Returns:
        Confirmation message
    """
    branch_name = _container_context.get("branch_name")
    if not branch_name:
        return "Error: No container context set."
    
    try:
        dev_container_manager.stop(branch_name)
        return f"DB container stopped: {branch_name}"
    except Exception as e:
        return f"Error stopping DB container: {str(e)}"


def get_container_tools() -> list:
    """Get all container tools for LLM."""
    return [
        container_exec,
        container_logs,
        container_status,
        container_start,
        container_stop,
    ]
