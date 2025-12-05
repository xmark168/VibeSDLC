"""Project Workspace Manager for Developer V2."""

import logging
import shutil
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)


class ProjectWorkspaceManager:
    """Manages project workspaces and task branches."""

    def __init__(self, project_id: UUID):
        self.project_id = project_id
        
        # Find backend root (backend/app/agents/developer_v2 → backend)
        current_file = Path(__file__).resolve()
        # workspace_manager.py → developer_v2 → agents → app → backend
        self.backend_root = current_file.parent.parent.parent.parent

        # Projects workspace root (shared with developer for now)
        self.workspace_root = self.backend_root / "app" / "agents" / "developer" / "projects_workspace"

        # This project's directory
        self.project_dir = self.workspace_root / f"project_{project_id}"

        # Template directory - use actual nextjs boilerplate
        self.template_dir = self.backend_root / "app" / "agents" / "templates" / "boilerplate" / "nextjs-boilerplate"

    def get_main_workspace(self) -> Path:
        """Get or create the main workspace (ws_main) for the project."""
        main_workspace = self.project_dir / "ws_main"

        if not main_workspace.exists():
            self._initialize_workspace(main_workspace)
            logger.info(f"Created main workspace for project {self.project_id}")
        else:
            logger.debug(f"Using existing main workspace for project {self.project_id}")

        return main_workspace

    def get_task_workspace(self, story_id: str) -> Path:
        """Get the path for a task-specific workspace."""
        short_story_id = story_id.split('-')[-1] if '-' in story_id else story_id[:8]
        return self.project_dir / f"ws_story_{short_story_id}"

    def _initialize_workspace(self, workspace_path: Path):
        """Initialize a new workspace from template."""
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        workspace_path.parent.mkdir(parents=True, exist_ok=True)

        def ignore_patterns(directory, files):
            ignore_dirs = {
                'node_modules', '.next', 'build', 'dist', 'out', '.turbo',
                '.cache', 'coverage', '.swc', '__pycache__', '.pytest_cache',
                '.venv', 'venv'
            }
            ignore = set()
            for file in files:
                if file in ignore_dirs:
                    ignore.add(file)
                # Note: .env is NOT ignored - workspace needs env vars for build/test
                # Note: bun.lock and .bun are NOT ignored - keeps dependency cache
                elif file in {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'}:
                    ignore.add(file)
            return ignore

        shutil.copytree(self.template_dir, workspace_path, ignore=ignore_patterns)
        logger.info(f"Initialized workspace from template: {workspace_path}")
