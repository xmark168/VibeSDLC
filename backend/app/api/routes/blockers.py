"""API routes for Blocker management."""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser, SessionDep
from app.models import Story
from app.schemas import BlockerCreate, BlockerPublic, BlockersPublic
from app.crud import blocker as crud_blocker

router = APIRouter(prefix="/blockers", tags=["blockers"])


@router.post("/", response_model=BlockerPublic)
def create_blocker(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    blocker_in: BlockerCreate,
) -> BlockerPublic:
    """Create a new blocker for a story."""
    # Validate story exists
    story = session.get(Story, blocker_in.backlog_item_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    blocker = crud_blocker.create_blocker(
        session=session,
        blocker_in=blocker_in,
        reported_by_user_id=current_user.id,
    )
    return BlockerPublic.model_validate(blocker)


@router.get("/story/{story_id}", response_model=BlockersPublic)
def get_blockers_by_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: UUID,
) -> BlockersPublic:
    """Get all blockers for a story."""
    blockers = crud_blocker.get_blockers_by_backlog_item(
        session=session,
        backlog_item_id=story_id,
    )
    return BlockersPublic(data=blockers, count=len(blockers))


@router.get("/project/{project_id}", response_model=BlockersPublic)
def get_blockers_by_project(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID,
) -> BlockersPublic:
    """Get all blockers for a project."""
    blockers = crud_blocker.get_blockers_by_project(
        session=session,
        project_id=project_id,
    )
    return BlockersPublic(data=blockers, count=len(blockers))
