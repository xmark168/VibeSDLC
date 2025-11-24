"""Project Service - Encapsulates all project-related business logic."""

import logging
import re
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, func

from app.models import Project
from app.schemas import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project management."""

    def __init__(self, session: Session):
        self.session = session

    # ===== Internal Methods =====

    def generate_code(self) -> str:
        """
        Generate a unique project code in format PRJ-001, PRJ-002, etc.

        Logic:
        1. Find the highest existing project code
        2. Extract the number part
        3. Increment by 1
        4. Format as PRJ-XXX (pad to 3 digits)

        Returns:
            str: Generated project code (e.g., 'PRJ-001')
        """
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

        # Prepare update dict with required fields
        update_dict = {
            "code": project_code,
            "owner_id": owner_id,
            "is_init": False,  # Default value for new projects
        }

        # Create project with auto-generated code
        db_project = Project.model_validate(
            project_in,
            update=update_dict,
        )

        self.session.add(db_project)
        self.session.commit()
        self.session.refresh(db_project)

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

        # Prepare update dict with required fields
        update_dict = {
            "code": project_code,
            "owner_id": owner_id,
            "is_init": False,  # Default value for new projects
        }

        # Create project with auto-generated code
        db_project = Project.model_validate(
            project_in,
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
        db_project.sqlmodel_update(project_data)

        self.session.add(db_project)
        self.session.commit()
        self.session.refresh(db_project)

        logger.info(f"Updated project {db_project.code} (ID: {db_project.id})")
        return db_project

    def delete(self, project_id: UUID) -> None:
        """
        Delete a project by ID.

        Args:
            project_id: UUID of the project to delete
        """
        db_project = self.session.get(Project, project_id)
        if db_project:
            self.session.delete(db_project)
            self.session.commit()
            logger.info(f"Deleted project {db_project.code} (ID: {project_id})")
