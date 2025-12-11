"""Seed tech stack configurations for projects."""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Tech stack configurations with boilerplate paths and build commands
TECH_STACK_CONFIGS = {
    "nextjs": {
        "name": "Next.js",
        "boilerplate_dir": "nextjs-boilerplate",
        "service": [
            {
                "name": "app",
                "path": ".",
                "format_cmd": "pnpm run format",
                "lint_fix_cmd": "pnpm run lint:fix",
                "typecheck_cmd": "pnpm run typecheck",
                "build_cmd": "pnpm run build",
            }
        ],
    },
    "nodejs-react": {
        "name": "Node.js + React",
        "boilerplate_dir": "nextjs-boilerplate",
        "service": [
            {
                "name": "app",
                "path": ".",
                "format_cmd": "pnpm run format",
                "lint_fix_cmd": "pnpm run lint:fix",
                "typecheck_cmd": "pnpm run typecheck",
                "build_cmd": "pnpm run build",
            }
        ],
    },
    "python-fastapi": {
        "name": "Python FastAPI",
        "boilerplate_dir": None,  # No boilerplate yet
        "service": [
            {
                "name": "backend",
                "path": ".",
                "format_cmd": "ruff format .",
                "lint_fix_cmd": "ruff check --fix .",
                "typecheck_cmd": "mypy .",
                "build_cmd": "",
            }
        ],
    },
}


def get_tech_stack_config(tech_stack: str) -> dict:
    """Get tech stack configuration by name."""
    return TECH_STACK_CONFIGS.get(tech_stack, TECH_STACK_CONFIGS.get("nextjs"))


def get_boilerplate_path(tech_stack: str) -> Path | None:
    """Get boilerplate directory path for a tech stack."""
    config = get_tech_stack_config(tech_stack)
    if not config or not config.get("boilerplate_dir"):
        return None
    
    backend_root = Path(__file__).resolve().parent.parent.parent
    return backend_root / "app" / "agents" / "templates" / "boilerplate" / config["boilerplate_dir"]


def copy_boilerplate_to_project(tech_stack: str, project_path: Path) -> bool:
    """Copy boilerplate template to project path.
    
    Args:
        tech_stack: Tech stack name (e.g., 'nextjs', 'nodejs-react')
        project_path: Destination path for the project
        
    Returns:
        True if successful, False otherwise
    """
    boilerplate_path = get_boilerplate_path(tech_stack)
    
    if not boilerplate_path or not boilerplate_path.exists():
        logger.warning(f"No boilerplate found for tech stack: {tech_stack}")
        return False
    
    try:
        # Create parent directory if not exists
        project_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ignore patterns for copy
        def ignore_patterns(directory, files):
            ignore_dirs = {
                'node_modules', '.next', 'build', 'dist', 'out', '.turbo',
                '.cache', 'coverage', '.swc', '__pycache__', '.pytest_cache', 
                '.venv', 'venv', '.git'
            }
            ignore_files = {'package-lock.json', 'yarn.lock', 'bun.lockb'}  # Keep pnpm-lock.yaml
            return {f for f in files if f in ignore_dirs or f in ignore_files}
        
        # Copy boilerplate to project path
        if project_path.exists():
            logger.info(f"Project path already exists: {project_path}")
            return True
            
        shutil.copytree(boilerplate_path, project_path, ignore=ignore_patterns)
        logger.info(f"Copied boilerplate '{tech_stack}' to {project_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy boilerplate: {e}")
        return False


def init_git_repo(project_path: Path) -> bool:
    """Initialize git repository in project path."""
    import subprocess
    
    try:
        subprocess.run(
            ["git", "init"],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit from boilerplate"],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Initialized git repo at {project_path}")
        return True
    except Exception as e:
        logger.warning(f"Failed to init git repo: {e}")
        return False


if __name__ == "__main__":
    print("Tech Stack Configurations:")
    print("=" * 50)
    for key, config in TECH_STACK_CONFIGS.items():
        print(f"\n{key}:")
        print(f"  Name: {config['name']}")
        print(f"  Boilerplate: {config['boilerplate_dir']}")
        print(f"  Services: {len(config['service'])}")
