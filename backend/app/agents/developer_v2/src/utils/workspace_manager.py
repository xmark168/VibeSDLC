"""Project Workspace Manager"""

import logging
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)


class ProjectWorkspaceManager:
    """
    Git worktree manager
    """
    def __init__(self, project_id: UUID):
        self.project_id = project_id
        self._project_path = None
        self._load_project_path()

    def _load_project_path(self):
        """Load project_path from database."""
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Project
        
        with Session(engine) as session:
            project = session.get(Project, self.project_id)
            if project and project.project_path:
                # Convert relative path to absolute
                backend_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
                self._project_path = (backend_root / project.project_path).resolve()
                logger.info(f"Loaded project path from DB: {self._project_path}")
            else:
                logger.warning(f"Project {self.project_id} has no project_path, using fallback")
                backend_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
                self._project_path = backend_root / "projects" / str(self.project_id)

    def get_main_workspace(self) -> Path:
        """Get main workspace path (project_path from DB)."""
        if not self._project_path.exists():
            logger.warning(f"Project path does not exist: {self._project_path}")
        return self._project_path

    def get_task_workspace(self, story_id: str) -> Path:
        """Get worktree path for a story: {project_path}_{story_id}"""
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        return Path(f"{self._project_path}_{short_id}")
