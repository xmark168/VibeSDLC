"""Kanban WIP limits API."""
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from typing import Any
from app.api.deps import get_current_user, get_db
from app.models import User
from app.services import KanbanService
from app.schemas import WIPLimitUpdate, WIPLimitPublic, WIPLimitsPublic

router = APIRouter(tags=["kanban"])


def get_kanban_service(db: Session = Depends(get_db)) -> KanbanService:
    return KanbanService(db)


@router.get("/projects/{project_id}/wip-limits", response_model=WIPLimitsPublic)
def get_wip_limits(
    project_id: UUID,
    _: User = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service)
) -> Any:
    """Get all WIP limits."""
    limits = kanban_service.get_all_wip_limits(project_id)
    return WIPLimitsPublic(data=limits, count=len(limits))


@router.get("/projects/{project_id}/wip-limits/dynamic", response_model=dict)
def get_project_dynamic_wip(
    project_id: UUID,
    _: User = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service)
) -> dict:
    """Get dynamic WIP limits with usage."""
    dynamic_limits = kanban_service.get_dynamic_wip_with_usage(project_id)
    return {"project_id": str(project_id), "dynamic_limits": dynamic_limits}


@router.put("/projects/{project_id}/wip-limits/{column_name}", response_model=WIPLimitPublic)
def update_wip_limit(
    project_id: UUID,
    column_name: str,
    limit_update: WIPLimitUpdate,
    current_user: User = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service)
) -> Any:
    """Update WIP limit for a column."""
    try:
        return kanban_service.update_wip_limit(
            project_id=project_id,
            column_name=column_name,
            wip_limit=limit_update.wip_limit,
            limit_type=limit_update.limit_type or "hard"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/projects/{project_id}/stories/{story_id}/validate-wip")
def validate_wip_before_move(
    project_id: UUID,
    story_id: UUID,
    target_status: str,
    current_user: User = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service)
) -> dict:
    """Validate WIP before moving story."""
    try:
        allowed, violation = kanban_service.validate_wip_move(
            project_id=project_id, story_id=story_id, target_status=target_status
        )
        if not allowed:
            return {"allowed": False, "violation": violation}
        elif violation:
            return {"allowed": True, "violation": violation, "warning": True}
        return {"allowed": True, "violation": None}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



