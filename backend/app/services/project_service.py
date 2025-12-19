"""Project Service - Encapsulates all project-related business logic."""

import logging
import re
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, func

from app.models import Project
from app.schemas import ProjectCreate, ProjectUpdate
from app.utils.seed_techstacks import copy_boilerplate_to_project, init_git_repo

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, session: Session):
        self.session = session

    def generate_code(self) -> str:
        """ Generate a unique project code in format PRJ-001, PRJ-002, etc.        """
        # Get all project codes from database
        statement = select(Project.code).order_by(Project.code.desc())
        result = self.session.exec(statement).first()

        if not result:
            # No projects exist yet, start from PRJ-001
            return "PRJ-001"

        # Extract number from code (e.g., "PRJ-005" -> 5)
        match = re.match(r"PRJ-(\d+)", result)
        if match:
            current_number = int(match.group(1))
            next_number = current_number + 1
        else:
            # Fallback if format is unexpected
            next_number = 1

        # Format as PRJ-XXX
        return f"PRJ-{next_number:03d}"

    def create(self, project_in: ProjectCreate, owner_id: UUID) -> Project:
        """
        Create a new project with auto-generated code.

        Args:
            project_in: Project creation schema
            owner_id: UUID of the project owner

        Returns:
            Project: Created project instance
        """
        # Generate unique project code
        project_code = self.generate_code()

        # Convert ProjectCreate to dict and handle tech_stack conversion
        project_dict = project_in.model_dump()
        
        # Convert tech_stack from list to string for database compatibility
        if project_dict.get('tech_stack') and isinstance(project_dict['tech_stack'], list):
            project_dict['tech_stack'] = project_dict['tech_stack'][0] if project_dict['tech_stack'] else "nodejs-react"

        tech_stack = project_dict.get('tech_stack', 'nodejs-react')

        # Prepare update dict with required fields
        update_dict = {
            "code": project_code,
            "owner_id": owner_id,
            "is_init": False,  # Default value for new projects
        }

        # Create project with auto-generated code
        db_project = Project.model_validate(
            project_dict,
            update=update_dict,
        )

        self.session.add(db_project)
        self.session.commit()
        self.session.refresh(db_project)

        # Setup project directory with boilerplate
        backend_root = Path(__file__).resolve().parent.parent.parent
        project_path = backend_root / "projects" / str(db_project.id)
        
        # Copy boilerplate based on tech stack
        if copy_boilerplate_to_project(tech_stack, project_path):
            # Initialize git repo
            init_git_repo(project_path)
            
            # Update project with path
            db_project.project_path = f"projects/{db_project.id}"
            self.session.add(db_project)
            self.session.commit()
            self.session.refresh(db_project)
            logger.info(f"Setup project directory at {project_path}")

        logger.info(f"Created project {db_project.code} (ID: {db_project.id}) for user {owner_id}")
        return db_project

    def create_no_commit(self, project_in: ProjectCreate, owner_id: UUID) -> Project:
        """
        Create a new project without committing - for use in larger transactions.

        Args:
            project_in: Project creation schema
            owner_id: UUID of the project owner

        Returns:
            Project: Created project instance (not committed)
        """
        # Generate unique project code
        project_code = self.generate_code()

        # Convert ProjectCreate to dict and handle tech_stack conversion
        project_dict = project_in.model_dump()
        
        # Convert tech_stack from list to string for database compatibility
        if project_dict.get('tech_stack') and isinstance(project_dict['tech_stack'], list):
            project_dict['tech_stack'] = project_dict['tech_stack'][0] if project_dict['tech_stack'] else "nodejs-react"

        # Prepare update dict with required fields
        update_dict = {
            "code": project_code,
            "owner_id": owner_id,
            "is_init": False,  # Default value for new projects
        }

        # Create project with auto-generated code
        db_project = Project.model_validate(
            project_dict,
            update=update_dict,
        )

        self.session.add(db_project)
        # Flush to get the ID without committing
        self.session.flush()

        logger.info(f"Prepared project {db_project.code} (ID: {db_project.id}) for user {owner_id}")
        return db_project

    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        """
        Get a project by ID.

        Args:
            project_id: UUID of the project

        Returns:
            Project or None if not found
        """
        return self.session.get(Project, project_id)

    def get_all(self, skip: int = 0, limit: int = 100) -> tuple[list[Project], int]:
        """
        Get all projects with pagination (for admin).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (projects list, total count)
        """
        # Get total count
        count_statement = select(func.count(Project.id))
        total_count = self.session.exec(count_statement).one()

        # Get paginated results
        statement = (
            select(Project)
            .offset(skip)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        projects = self.session.exec(statement).all()

        return projects, total_count

    def get_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Project], int]:
        """
        Get all projects owned by a user with pagination.

        Args:
            owner_id: UUID of the project owner
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (projects list, total count)
        """
        # Get total count
        count_statement = select(func.count(Project.id)).where(Project.owner_id == owner_id)
        total_count = self.session.exec(count_statement).one()

        # Get paginated results
        statement = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        projects = self.session.exec(statement).all()

        return projects, total_count

    def update(self, db_project: Project, project_in: ProjectUpdate) -> Project:
        """
        Update a project.

        Args:
            db_project: Project instance to update
            project_in: Project update schema

        Returns:
            Project: Updated project instance
        """
        project_data = project_in.model_dump(exclude_unset=True)
        
        # Convert tech_stack from list to string for database compatibility
        if 'tech_stack' in project_data and isinstance(project_data['tech_stack'], list):
            project_data['tech_stack'] = project_data['tech_stack'][0] if project_data['tech_stack'] else None
        
        db_project.sqlmodel_update(project_data)

        self.session.add(db_project)
        self.session.commit()
        self.session.refresh(db_project)

        logger.info(f"Updated project {db_project.code} (ID: {db_project.id})")
        return db_project

    def delete(self, project_id: UUID) -> None:
        """
        Delete a project by ID (DB only, no file cleanup).

        Args:
            project_id: UUID of the project to delete
        """
        db_project = self.session.get(Project, project_id)
        if db_project:
            self.session.delete(db_project)
            self.session.commit()
            logger.info(f"Deleted project {db_project.code} (ID: {project_id})")

    def delete_with_cleanup(self, project_id: UUID) -> None:
        """
        Delete a project and clean up all associated files (workspace + worktrees).

        Args:
            project_id: UUID of the project to delete
        """
        import shutil
        import time
        
        def force_remove_tree(path: Path) -> bool:
            """Force remove directory tree."""
            if not path.exists():
                return True
            try:
                shutil.rmtree(path)
                return True
            except Exception as e:
                logger.warning(f"Failed to remove {path}: {e}")
                return False
        
        db_project = self.session.get(Project, project_id)
        if not db_project:
            return
        
        project_code = db_project.code
        
        # Clean up worktrees first
        self.cleanup_worktrees(project_id)
        
        # Clean up main project directory
        if db_project.project_path:
            backend_root = Path(__file__).resolve().parent.parent.parent
            project_dir = backend_root / db_project.project_path
            
            if project_dir.exists():
                # First try to remove .next and node_modules (common large dirs)
                for subdir in ['.next', 'node_modules', '.worktrees']:
                    subpath = project_dir / subdir
                    if subpath.exists():
                        force_remove_tree(subpath)
                
                # Then remove the main directory
                if force_remove_tree(project_dir):
                    logger.info(f"Deleted project directory: {project_dir}")
                else:
                    logger.error(f"Failed to fully delete project directory {project_dir}")
        
        # Delete from database regardless of file cleanup result
        self.session.delete(db_project)
        self.session.commit()
        logger.info(f"Deleted project {project_code} (ID: {project_id}) with cleanup")

    def cleanup_worktrees(self, project_id: UUID) -> int:
        """
        Clean up all worktrees for a project.
        
        Worktrees are named: {project_path}_{story_id_suffix}
        
        Args:
            project_id: UUID of the project
            
        Returns:
            int: Number of worktrees deleted
        """
        import shutil
        
        db_project = self.session.get(Project, project_id)
        if not db_project or not db_project.project_path:
            return 0
        
        backend_root = Path(__file__).resolve().parent.parent.parent
        project_dir = backend_root / db_project.project_path
        
        if not project_dir.exists():
            return 0
        
        # Find worktrees: directories that start with project_path + "_"
        parent_dir = project_dir.parent
        project_name = project_dir.name
        
        deleted_count = 0
        for item in parent_dir.iterdir():
            if item.is_dir() and item.name.startswith(f"{project_name}_"):
                try:
                    shutil.rmtree(item)
                    logger.info(f"Deleted worktree: {item}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete worktree {item}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} worktrees for project {project_id}")
        return deleted_count
