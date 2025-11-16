"""CRUD operations for Blocker model."""

from uuid import UUID
from sqlmodel import Session, select
from app.models import Blocker
from app.schemas import BlockerCreate


def create_blocker(
    *,
    session: Session,
    blocker_in: BlockerCreate,
    reported_by_user_id: UUID,
) -> Blocker:
    """Create a new blocker."""
    db_blocker = Blocker(
        backlog_item_id=blocker_in.backlog_item_id,
        reported_by_user_id=reported_by_user_id,
        blocker_type=blocker_in.blocker_type,
        description=blocker_in.description,
    )
    session.add(db_blocker)
    session.commit()
    session.refresh(db_blocker)
    return db_blocker


def get_blockers_by_backlog_item(
    *,
    session: Session,
    backlog_item_id: UUID,
) -> list[Blocker]:
    """Get all blockers for a backlog item."""
    statement = select(Blocker).where(Blocker.backlog_item_id == backlog_item_id)
    return list(session.exec(statement).all())


def get_blockers_by_project(
    *,
    session: Session,
    project_id: UUID,
) -> list[Blocker]:
    """Get all blockers for a project."""
    from app.models import BacklogItem

    statement = (
        select(Blocker)
        .join(BacklogItem)
        .where(BacklogItem.project_id == project_id)
    )
    return list(session.exec(statement).all())
