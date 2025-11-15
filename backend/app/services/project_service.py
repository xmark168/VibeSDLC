"""
Project Service - Business logic for project and Kanban board management
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models import Project, User, Epic, Story, Agent
from app.kanban_schemas import ProjectCreate, ProjectUpdate, ProjectCreateInternal, ProjectResponse
from app.dependencies import get_project_or_404, verify_project_owner
from app.enums import StoryStatus, AgentType


# Default Kanban Policy following Lean Kanban principles
DEFAULT_KANBAN_POLICY = {
    "version": "1.0",
    "columns": [
        {
            "status": "TODO",
            "name": "Backlog",
            "wip_limit": None,
            "position": 0,
            "description": "Stories ready to be started"
        },
        {
            "status": "IN_PROGRESS",
            "name": "In Progress",
            "wip_limit": 3,
            "position": 1,
            "description": "Stories currently being worked on"
        },
        {
            "status": "REVIEW",
            "name": "Code Review",
            "wip_limit": 2,
            "position": 2,
            "description": "Stories under review"
        },
        {
            "status": "TESTING",
            "name": "Testing",
            "wip_limit": 2,
            "position": 3,
            "description": "Stories being tested"
        },
        {
            "status": "DONE",
            "name": "Completed",
            "wip_limit": None,
            "position": 4,
            "description": "Completed stories"
        },
        {
            "status": "BLOCKED",
            "name": "Blocked",
            "wip_limit": None,
            "position": 5,
            "description": "Stories that are blocked"
        },
        {
            "status": "ARCHIVED",
            "name": "Archived",
            "wip_limit": None,
            "position": 6,
            "description": "Archived stories"
        }
    ],
    "workflow_rules": {
        "allowed_transitions": {
            "TODO": ["IN_PROGRESS"],
            "IN_PROGRESS": ["REVIEW", "BLOCKED"],
            "REVIEW": ["IN_PROGRESS", "TESTING", "BLOCKED"],
            "TESTING": ["REVIEW", "DONE", "BLOCKED"],
            "BLOCKED": ["TODO", "IN_PROGRESS", "REVIEW", "TESTING"],
            "DONE": ["ARCHIVED"],
            "ARCHIVED": []
        },
        "completion_requirements": {
            "acceptance_criteria_required": True,
            "min_agents_assigned": 1
        }
    }
}


class ProjectService:
    """Service for managing projects and Kanban boards"""

    @staticmethod
    async def create(data: ProjectCreate, current_user: User, db: AsyncSession) -> Project:
        """
        Create a new project with default Kanban policy and 4 default agents

        Args:
            data: Project creation data
            current_user: Current authenticated user (will be owner)
            db: Database session

        Returns:
            Created project with default agents

        Raises:
            HTTPException: 400 if project code already exists
        """
        # 1. Check if project with same code already exists
        stmt = select(Project).where(
            Project.code == data.code,
            Project.deleted_at == None
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with code '{data.code}' already exists"
            )

        # 2. Set kanban policy to default if not provided
        kanban_policy = data.kanban_policy or DEFAULT_KANBAN_POLICY

        # 3. Create project
        project = Project(
            code=data.code,
            name=data.name,
            working_directory=data.working_directory,
            owner_id=current_user.id,
            tech_stack_id=data.tech_stack_id,
            kanban_policy=kanban_policy
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        # 4. Create 4 default agents for the project
        default_agents = [
            {
                "name": f"{project.code}-FLOW_MANAGER",
                "type": AgentType.FLOW_MANAGER,
                "description": "Coordinates workflow, manages task distribution, and ensures smooth project execution",
                "capacity": 5
            },
            {
                "name": f"{project.code}-BUSINESS_ANALYST",
                "type": AgentType.BUSINESS_ANALYST,
                "description": "Analyzes requirements, refines user stories, and ensures business value alignment",
                "capacity": 5
            },
            {
                "name": f"{project.code}-DEVELOPER",
                "type": AgentType.DEVELOPER,
                "description": "Implements features, writes code, and delivers technical solutions",
                "capacity": 5
            },
            {
                "name": f"{project.code}-TESTER",
                "type": AgentType.TESTER,
                "description": "Validates functionality, ensures quality, and performs comprehensive testing",
                "capacity": 5
            }
        ]

        for agent_data in default_agents:
            agent = Agent(
                project_id=project.id,
                name=agent_data["name"],
                type=agent_data["type"],
                description=agent_data["description"],
                capacity=agent_data["capacity"],
                is_active=True
            )
            db.add(agent)

        await db.commit()
        await db.refresh(project)

        return project

    @staticmethod
    async def get_user_projects(current_user: User, db: AsyncSession) -> List[Project]:
        """
        Get all projects owned by user

        Args:
            current_user: Current authenticated user
            db: Database session

        Returns:
            List of projects
        """
        stmt = select(Project).where(
            Project.owner_id == current_user.id,
            Project.deleted_at == None
        )
        result = await db.execute(stmt)
        projects = result.scalars().all()
        return list(projects)

    @staticmethod
    async def get_by_id(project_id: int, db: AsyncSession) -> Project:
        """
        Get project by ID

        Args:
            project_id: Project ID
            db: Database session

        Returns:
            Project

        Raises:
            HTTPException: 404 if not found
        """
        return await get_project_or_404(project_id, db)

    @staticmethod
    async def update(
        project_id: int,
        data: ProjectUpdate,
        current_user: User,
        db: AsyncSession
    ) -> Project:
        """
        Update project

        Args:
            project_id: Project ID
            data: Update data
            current_user: Current authenticated user
            db: Database session

        Returns:
            Updated project

        Raises:
            HTTPException: 404 if not found
            HTTPException: 403 if user is not owner
            HTTPException: 400 if code conflict
        """
        # 1. Get existing project
        project = await get_project_or_404(project_id, db)

        # 2. Verify ownership
        await verify_project_owner(project, current_user)

        # 3. Check code conflict if code is being changed
        if data.code and data.code != project.code:
            stmt = select(Project).where(
                Project.code == data.code,
                Project.deleted_at == None
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Project with code '{data.code}' already exists"
                )

        # 4. Update project
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(project, key, value)
        await db.commit()
        await db.refresh(project)

        return project

    @staticmethod
    async def update_kanban_policy(
        project_id: int,
        policy: dict,
        current_user: User,
        db: AsyncSession
    ) -> Project:
        """
        Update project Kanban policy

        Args:
            project_id: Project ID
            policy: New Kanban policy
            current_user: Current authenticated user
            db: Database session

        Returns:
            Updated project

        Raises:
            HTTPException: 404 if not found
            HTTPException: 403 if user is not owner
            HTTPException: 400 if policy structure is invalid
        """
        # 1. Get existing project
        project = await get_project_or_404(project_id, db)

        # 2. Verify ownership
        await verify_project_owner(project, current_user)

        # 3. Validate policy structure
        ProjectService._validate_kanban_policy(policy)

        # 4. Update policy
        project.kanban_policy = policy
        await db.commit()
        await db.refresh(project)

        return project

    @staticmethod
    def _validate_kanban_policy(policy: dict) -> None:
        """
        Validate Kanban policy structure

        Args:
            policy: Policy dictionary

        Raises:
            HTTPException: 400 if invalid structure
        """
        if not isinstance(policy, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kanban policy must be a JSON object"
            )

        if "columns" not in policy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kanban policy must have 'columns' field"
            )

        if "workflow_rules" not in policy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kanban policy must have 'workflow_rules' field"
            )

        # Validate columns structure
        columns = policy.get("columns", [])
        if not isinstance(columns, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'columns' must be an array"
            )

        for col in columns:
            if "status" not in col or "name" not in col:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each column must have 'status' and 'name'"
                )

    @staticmethod
    async def get_board_view(project_id: int, db: AsyncSession) -> dict:
        """
        Get Kanban board view with stories grouped by status

        Args:
            project_id: Project ID
            db: Database session

        Returns:
            Board view with columns and stories

        Raises:
            HTTPException: 404 if project not found
        """
        # 1. Get project
        project = await get_project_or_404(project_id, db)

        # 2. Get kanban policy
        policy = project.kanban_policy or DEFAULT_KANBAN_POLICY

        # 3. Get all stories for this project (via epics)
        query = (
            select(Story)
            .join(Epic, Story.epic_id == Epic.id)
            .where(
                Epic.project_id == project_id,
                Story.deleted_at == None,
                Epic.deleted_at == None
            )
            .order_by(Story.created_at.desc())
        )
        result = await db.execute(query)
        all_stories = result.scalars().all()

        # 4. Group stories by status
        stories_by_status = {}
        for story in all_stories:
            if story.status not in stories_by_status:
                stories_by_status[story.status] = []
            stories_by_status[story.status].append(story)

        # 5. Build columns
        columns = []
        for col_config in policy.get("columns", []):
            status = col_config["status"]
            stories_in_column = stories_by_status.get(status, [])

            columns.append({
                "status": status,
                "name": col_config["name"],
                "wip_limit": col_config.get("wip_limit"),
                "current_count": len(stories_in_column),
                "is_over_limit": (
                    col_config.get("wip_limit") is not None and
                    len(stories_in_column) > col_config["wip_limit"]
                ),
                "stories": stories_in_column,
                "position": col_config.get("position", 0)
            })

        # 6. Count blocked stories
        blocked_count = len(stories_by_status.get("BLOCKED", []))

        return {
            "project_id": project_id,
            "project_name": project.name,
            "columns": sorted(columns, key=lambda x: x["position"]),
            "total_stories": len(all_stories),
            "blocked_count": blocked_count
        }

    @staticmethod
    async def delete(project_id: int, current_user: User, db: AsyncSession) -> None:
        """
        Soft delete project

        Args:
            project_id: Project ID
            current_user: Current authenticated user
            db: Database session

        Raises:
            HTTPException: 404 if not found
            HTTPException: 403 if user is not owner
        """
        # 1. Get existing project
        project = await get_project_or_404(project_id, db)

        # 2. Verify ownership
        await verify_project_owner(project, current_user)

        # 3. Soft delete (set deleted_at)
        project.deleted_at = datetime.utcnow()
        await db.commit()
