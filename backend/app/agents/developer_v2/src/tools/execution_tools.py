"""Execution Tools - Command and test execution utilities (MetaGPT-inspired)."""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CommandResult:
    """Result of executing a command."""
    def __init__(self, stdout: str, stderr: str, returncode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.success = returncode == 0


async def install_dependencies(workspace_path: str) -> bool:
    """Install dependencies for the workspace (MetaGPT RunCode pattern).
    
    Args:
        workspace_path: Path to the workspace
        
    Returns:
        True if dependencies were installed, False otherwise
    """
    workspace = Path(workspace_path)
    installed = False
    
    # Python: requirements.txt
    requirements_txt = workspace / "requirements.txt"
    if requirements_txt.exists() and requirements_txt.stat().st_size > 0:
        try:
            logger.info(f"Installing Python dependencies from {requirements_txt}")
            subprocess.run(
                ["python", "-m", "pip", "install", "-r", "requirements.txt", "-q"],
                cwd=workspace_path,
                check=False,
                timeout=120
            )
            installed = True
        except Exception as e:
            logger.warning(f"Failed to install requirements.txt: {e}")
    
    # Python: Install pytest for testing
    py_files = list(workspace.glob("**/*.py"))
    if py_files:
        try:
            subprocess.run(
                ["python", "-m", "pip", "install", "pytest", "-q"],
                cwd=workspace_path,
                check=False,
                timeout=60
            )
            installed = True
        except Exception as e:
            logger.warning(f"Failed to install pytest: {e}")
    
    # Node.js: package.json
    package_json = workspace / "package.json"
    if package_json.exists():
        try:
            logger.info(f"Installing Node.js dependencies from {package_json}")
            use_shell = sys.platform == 'win32'
            
            if (workspace / "bun.lock").exists() or (workspace / "bun.lockb").exists():
                subprocess.run("bun install", cwd=workspace_path, check=False, timeout=180, shell=use_shell)
            elif (workspace / "pnpm-lock.yaml").exists():
                subprocess.run("pnpm install", cwd=workspace_path, check=False, timeout=180, shell=use_shell)
            else:
                subprocess.run("npm install", cwd=workspace_path, check=False, timeout=180, shell=use_shell)
            installed = True
        except Exception as e:
            logger.warning(f"Failed to install npm dependencies: {e}")
    
    return installed


def detect_test_command(workspace_path: str) -> List[str]:
    """Detect the appropriate test command for a workspace.
    
    Args:
        workspace_path: Path to the workspace
        
    Returns:
        List of command arguments
    """
    workspace = Path(workspace_path)
    
    if (workspace / "pytest.ini").exists() or (workspace / "pyproject.toml").exists():
        return ["python", "-m", "pytest", "-v"]
    
    if (workspace / "setup.py").exists():
        return ["python", "-m", "pytest", "-v"]
    
    package_json = workspace / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                pkg = json.load(f)
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                if (workspace / "bun.lockb").exists():
                    return ["bun", "test"]
                return ["npm", "test"]
        except Exception:
            pass
    
    py_files = list(workspace.glob("**/*.py"))
    if py_files:
        return ["python", "-m", "pytest", "-v"]
    
    js_files = list(workspace.glob("**/*.js")) + list(workspace.glob("**/*.ts"))
    if js_files:
        return ["npm", "test"]
    
    return ["echo", "No test framework detected"]


async def execute_command_async(
    command: List[str],
    working_directory: str,
    timeout: int = 60,
    env: Dict[str, str] = None
) -> CommandResult:
    """Execute a command asynchronously.
    
    Args:
        command: Command and arguments as list
        working_directory: Working directory for the command
        timeout: Timeout in seconds
        env: Optional environment variables
        
    Returns:
        CommandResult with stdout, stderr, and returncode
    """
    try:
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        pythonpath = process_env.get("PYTHONPATH", "")
        process_env["PYTHONPATH"] = f"{working_directory}:{pythonpath}"
        
        use_shell = sys.platform == 'win32' and command and command[0] in ['npm', 'pnpm', 'bun', 'npx']
        
        if use_shell:
            cmd_str = ' '.join(command)
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                cwd=working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env
            )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            return CommandResult(
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                returncode=process.returncode or 0
            )
        except asyncio.TimeoutError:
            process.kill()
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                returncode=-1
            )
            
    except Exception as e:
        return CommandResult(
            stdout="",
            stderr=f"Error executing command: {str(e)}",
            returncode=-1
        )


def find_test_file(workspace_path: str, source_file: str) -> Optional[str]:
    """Find the test file for a given source file.
    
    Args:
        workspace_path: Path to workspace
        source_file: Name of the source file
        
    Returns:
        Path to test file if found, None otherwise
    """
    workspace = Path(workspace_path)
    source_name = Path(source_file).stem
    
    patterns = [
        f"test_{source_name}.py",
        f"{source_name}_test.py",
        f"tests/test_{source_name}.py",
        f"test/test_{source_name}.py",
        f"__tests__/{source_name}.test.js",
        f"__tests__/{source_name}.test.ts",
        f"{source_name}.test.js",
        f"{source_name}.test.ts",
        f"{source_name}.spec.js",
        f"{source_name}.spec.ts",
    ]
    
    for pattern in patterns:
        matches = list(workspace.glob(f"**/{pattern}"))
        if matches:
            return str(matches[0].relative_to(workspace))
    
    return None
