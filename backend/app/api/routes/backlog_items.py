import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, func, col
from app.api.deps import CurrentUser, SessionDep
from app.models import BacklogItem, Sprint, IssueActivity
from app.schemas import (
    BacklogItemCreate,
    BacklogItemUpdate,
    BacklogItemPublic,
    BacklogItemsPublic
)

router = APIRouter(prefix="/backlog-items", tags=["backlog-items"])

@router.get("/", response_model=BacklogItemsPublic)
def get_backlog_items(
    session: SessionDep, 
    current_user: CurrentUser,
    sprint_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    assignee_id: Optional[uuid.UUID] = Query(None),
    type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Lấy danh sách backlog items với filter
    - sprint_id: Filter theo sprint
    - status: Filter theo trạng thái (Backlog, Todo, Doing, Done)
    - assignee_id: Filter theo người được assign
    - type: Filter theo loại (Epic, User Story, Task, Sub-task)
    """

    statement = select(BacklogItem)

    if sprint_id:
        statement = statement.where(BacklogItem.sprint_id == sprint_id)
    if status:
        statement = statement.where(BacklogItem.status == status)
    if assignee_id:
        statement = statement.where(BacklogItem.assignee_id == assignee_id)
    if type:
        statement = statement.where(BacklogItem.type == type)

    # Order by rank
    statement = statement.order_by(BacklogItem.rank)

    # Count
    count_statement = select(func.count()).select_from(BacklogItem)
    if sprint_id:
        count_statement = count_statement.where(BacklogItem.sprint_id == sprint_id)

    count = session.exec(count_statement).one()
    
    # Get items
    items = session.exec(statement.offset(skip).limit(limit)).all()

    return BacklogItemsPublic(
        data=items,
        count=count
    )

@router.get("/{item_id}", response_model=BacklogItemPublic)
def get_backlog_item(
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID
) -> Any: 
    """
    Lấy chi tiết một backlog item
    """
    item = session.get(BacklogItem, item_id)
    if not item: 
        raise HTTPException(status_code=404, detail="Backlog item not found")

    return item

@router.post("/", response_model=BacklogItemPublic)
def create_backlog_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_in: BacklogItemCreate
) -> Any:
    """
    Tạo backlog item mới
    """
    # Validate sprint exists
    sprint = session.get(Sprint, item_in.sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    # Auto assign rank nếu không có
    item_data = item_in.model_dump()
    if item_data["rank"] is None:
        max_rank_statement = select(func.max(BacklogItem.rank)).where(
            BacklogItem.sprint_id == item_in.sprint_id,
            BacklogItem.status == item_in.status
        )
        max_rank = session.exec(max_rank_statement).one()
        item_data["rank"] = (max_rank or 0) + 1

    item = BacklogItem(**item_data)
    session.add(item)
    session.commit()
    session.refresh(item)

    # Log activity
    activity = IssueActivity(
        issue_id=item.id,
        actor_id=str(current_user.id),
        actor_name=current_user.username,
        note="Created backlog item"
    )
    session.add(activity)
    session.commit()

    return item

@router.patch("/{item_id}", response_model=BacklogItemPublic)
def update_backlog_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID,
    item_in: BacklogItemUpdate
) -> Any:
    """
    Cập nhật backlog item
    """
    item = session.get(BacklogItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Backlog item not found")

    # Save old values for activity log
    old_status = item.status
    old_assignee_id = item.assignee_id
    old_title = item.title

    # Update
    update_data = item_in.model_dump(exclude_unset=True)
    item.sqlmodel_update(update_data)
    session.add(item)
    session.commit()
    session.refresh(item)

    # Log activity
    activity = IssueActivity(
        issue_id=item.id,
        actor_id=str(current_user.id),
        actor_name=current_user.username,
        title_from=old_title if item_in.title else None,
        title_to=item.title if item_in.title else None,
        status_from=old_status if item_in.status else None,
        status_to=item.status if item_in.status else None,
        assignee_from=str(old_assignee_id) if old_assignee_id and item_in.assignee_id else None,
        assignee_to=str(item.assignee_id) if item.assignee_id and item_in.assignee_id else None,
        note="Updated backlog item"
    )
    session.add(activity)
    session.commit()

    return item

@router.put("/{item_id}/move", response_model=BacklogItemPublic)
def move_backlog_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID,
    new_status: str = Query(..., description="Cột đích (Backlog, Todo, Doing, Done)"),
    new_rank: int = Query(..., description="Vị trí mới trong cột"),
    new_sprint_id: Optional[uuid.UUID] = Query(None, description="Sprint đích (nếu di chuyển sang sprint khác)")
) -> Any:
    """
    Di chuyển item giữa các cột hoặc trong cùng cột
    """
    item = session.get(BacklogItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Backlog item not found")

    old_status = item.status
    old_rank = item.rank
    old_sprint_id = item.sprint_id

    # Update status và sprint nếu có
    item.status = new_status
    if new_sprint_id:
        # Validate sprint
        sprint = session.get(Sprint, new_sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")
        item.sprint_id = new_sprint_id

    # Reorder items trong cột cũ (nếu di chuyển sang cột/sprint khác)
    if old_status != new_status or old_sprint_id != item.sprint_id:
        # Giảm rank của các items sau vị trí cũ
        statement = select(BacklogItem).where(
            BacklogItem.sprint_id == old_sprint_id,
            BacklogItem.status == old_status,
            BacklogItem.rank > old_rank
        )
        old_items = session.exec(statement).all()
        for old_item in old_items:
            old_item.rank -= 1
            session.add(old_item)

    # Reorder items trong cột mới
    statement = select(BacklogItem).where(
        BacklogItem.sprint_id == item.sprint_id,
        BacklogItem.status == new_status,
        BacklogItem.rank >= new_rank,
        BacklogItem.id != item_id
    )
    new_items = session.exec(statement).all()
    for new_item in new_items:
        new_item.rank += 1
        session.add(new_item)

    # Set new rank
    item.rank = new_rank
    session.add(item)
    session.commit()
    session.refresh(item)

    # Log activity
    activity = IssueActivity(
        issue_id=item.id,
        actor_id=str(current_user.id),
        actor_name=current_user.username,
        status_from=old_status,
        status_to=new_status,
        rank_from=old_rank,
        rank_to=new_rank,
        note=f"Moved from {old_status} to {new_status}"
    )
    session.add(activity)
    session.commit()

    return item

@router.delete("/{item_id}")
def delete_backlog_item(
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID
) -> dict:
    """
    Xóa backlog item
    """
    item = session.get(BacklogItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Backlog item not found")

    session.delete(item)
    session.commit()

    return {"message": "Backlog item deleted successfully"}

@router.get("/sprint/{sprint_id}/kanban")
def get_kanban_board(
    session: SessionDep,
    current_user: CurrentUser,
    sprint_id: uuid.UUID
) -> Any:
    """
    Lấy dữ liệu Kanban board, nhóm theo status
    """
    # Validate sprint
    sprint = session.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    # TraDS ============= Kanban Hierarchy Support: Load parent/children relationships
    from sqlalchemy.orm import selectinload
    statement = select(BacklogItem).where(
        BacklogItem.sprint_id == sprint_id
    ).options(
        selectinload(BacklogItem.parent),
        selectinload(BacklogItem.children)
    ).order_by(BacklogItem.status, BacklogItem.rank)

    items = session.exec(statement).all()

    # Group by status
    board = {
        "Backlog": [],
        "Todo": [],
        "Doing": [],
        "Done": []
    }

    for item in items:
        if item.status in board:
            board[item.status].append(BacklogItemPublic.model_validate(item))

    return {
        "sprint": sprint,
        "board": board
    }

