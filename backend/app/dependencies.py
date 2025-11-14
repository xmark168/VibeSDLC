from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
from app.database import get_db
from app.core.security import decode_access_token
from app.models import User, Project, Epic, Story
from app.schemas import UserResponse
from app.kanban_schemas import ProjectResponse, EpicResponse, StoryResponse

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency để lấy user hiện tại từ JWT token
    Sử dụng trong các protected routes
    """
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể nhận dạng thông tin bảo mật",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Lấy user từ database bằng SQLAlchemy
    stmt = select(User).where(User.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency để kiểm tra user có active không
    Sử dụng cho các route cần user phải active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# ==================== Kanban Authorization Helpers ====================

async def get_project_or_404(project_id: int, db: AsyncSession) -> Project:
    """
    Get project by ID or raise 404

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        Project object

    Raises:
        HTTPException: 404 if project not found or soft deleted
    """
    stmt = select(Project).where(Project.id == project_id, Project.deleted_at == None)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return project


async def verify_project_owner(project: Project, current_user: User) -> None:
    """
    Verify that current user is the project owner

    Args:
        project: Project object
        current_user: Current authenticated user

    Raises:
        HTTPException: 403 if user is not project owner
    """
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can perform this action"
        )


async def get_epic_with_project(epic_id: int, db: AsyncSession) -> tuple[Epic, Project]:
    """
    Get epic and its project

    Args:
        epic_id: Epic ID
        db: Database session

    Returns:
        Tuple of (Epic, Project)

    Raises:
        HTTPException: 404 if epic not found
    """
    stmt = select(Epic).where(Epic.id == epic_id, Epic.deleted_at == None)
    result = await db.execute(stmt)
    epic = result.scalar_one_or_none()
    if not epic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Epic with ID {epic_id} not found"
        )

    project = await get_project_or_404(epic.project_id, db)
    return epic, project


async def get_story_with_project(story_id: int, db: AsyncSession) -> tuple[Story, Project]:
    """
    Get story and its project (via epic)

    Args:
        story_id: Story ID
        db: Database session

    Returns:
        Tuple of (Story, Project)

    Raises:
        HTTPException: 404 if story not found
    """
    stmt = select(Story).where(Story.id == story_id, Story.deleted_at == None)
    result = await db.execute(stmt)
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with ID {story_id} not found"
        )

    epic, project = await get_epic_with_project(story.epic_id, db)
    return story, project
