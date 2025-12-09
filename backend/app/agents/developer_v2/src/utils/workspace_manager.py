"""Project Workspace Manager - Git worktree for isolated story development."""

import logging
import shutil
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)


class ProjectWorkspaceManager:
    """Git worktree manager. Structure: projects_workspace/project_{uuid}/ws_main/ + ws_story_{id}/"""

    def __init__(self, project_id: UUID):
        self.project_id = project_id
        current_file = Path(__file__).resolve()
        self.backend_root = current_file.parent.parent.parent.parent.parent.parent
        self.workspace_root = self.backend_root / "app" / "agents" / "developer" / "projects_workspace"
        self.project_dir = self.workspace_root / f"project_{project_id}"
        self.template_dir = self.backend_root / "app" / "agents" / "templates" / "boilerplate" / "nextjs-boilerplate"

    def get_main_workspace(self) -> Path:
        main_workspace = self.project_dir / "ws_main"
        if not main_workspace.exists():
            self._initialize_workspace(main_workspace)
            logger.info(f"Created main workspace for project {self.project_id}")
        return main_workspace

    def get_task_workspace(self, story_id: str) -> Path:
        short_id = story_id.split('-')[-1] if '-' in story_id else story_id[:8]
        return self.project_dir / f"ws_story_{short_id}"

    def _initialize_workspace(self, workspace_path: Path):
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template not found: {self.template_dir}")

        workspace_path.parent.mkdir(parents=True, exist_ok=True)

        def ignore_patterns(directory, files):
            ignore_dirs = {'node_modules', '.next', 'build', 'dist', 'out', '.turbo',
                          '.cache', 'coverage', '.swc', '__pycache__', '.pytest_cache', '.venv', 'venv'}
            return {f for f in files if f in ignore_dirs or f in {'package-lock.json', 'yarn.lock', 'bun.lockb'}}

        shutil.copytree(self.template_dir, workspace_path, ignore=ignore_patterns)
        logger.info(f"Initialized workspace: {workspace_path}")
