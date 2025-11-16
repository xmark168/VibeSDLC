"""API routes for Blocker management."""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser, SessionDep
from app.models import BacklogItem
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
    """Create a new blocker for a backlog item."""
    # Validate backlog item exists
    backlog_item = session.get(BacklogItem, blocker_in.backlog_item_id)
    if not backlog_item:
        raise HTTPException(status_code=404, detail="Backlog item not found")

    blocker = crud_blocker.create_blocker(
        session=session,
        blocker_in=blocker_in,
        reported_by_user_id=current_user.id,
    )
    return BlockerPublic.model_validate(blocker)


@router.get("/backlog-item/{backlog_item_id}", response_model=BlockersPublic)
def get_blockers_by_backlog_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    backlog_item_id: UUID,
) -> BlockersPublic:
    """Get all blockers for a backlog item."""
    blockers = crud_blocker.get_blockers_by_backlog_item(
        session=session,
        backlog_item_id=backlog_item_id,
    )
    return BlockersPublic(data=blockers, count=len(blockers))


@router.get("/sprint/{sprint_id}", response_model=BlockersPublic)
def get_blockers_by_sprint(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    sprint_id: UUID,
) -> BlockersPublic:
    """Get all blockers for a sprint."""
    blockers = crud_blocker.get_blockers_by_sprint(
        session=session,
        sprint_id=sprint_id,
    )
    return BlockersPublic(data=blockers, count=len(blockers))
