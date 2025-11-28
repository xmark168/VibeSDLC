"""Lean Kanban API endpoints for WIP limits, workflow policies, and flow metrics."""

from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from typing import Any

from app.api.deps import get_current_user, get_db
from app.models import User, Story
from app.services import KanbanService
from app.schemas import (
    WIPLimitUpdate, WIPLimitPublic, WIPLimitsPublic,
    WorkflowPolicyUpdate, WorkflowPolicyPublic, WorkflowPoliciesPublic,
    StoryFlowMetrics, ProjectFlowMetrics
)

router = APIRouter(tags=["lean-kanban"])


def get_kanban_service(db: Session = Depends(get_db)) -> KanbanService:
    return KanbanService(db)


@router.get("/projects/{project_id}/wip-limits", response_model=WIPLimitsPublic)
def get_wip_limits(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service)
) -> Any:
    """Get all WIP limits (dynamic InProgress/Review + manual other columns)."""
    limits = kanban_service.get_all_wip_limits(project_id)
    return WIPLimitsPublic(data=limits, count=len(limits))


@router.get("/projects/{project_id}/wip-limits/dynamic", response_model=dict)
def get_project_dynamic_wip(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service)
) -> dict:
    """Get dynamic WIP limits with current usage and available capacity."""
    dynamic_limits = kanban_service.get_dynamic_wip_with_usage(project_id)
    
    return {
        "project_id": str(project_id),
        "dynamic_limits": dynamic_limits,
        "info": "WIP limits are dynamically calculated from active agent count"
    }


@router.put("/projects/{project_id}/wip-limits/{column_name}", response_model=WIPLimitPublic)
def update_wip_limit(
    project_id: UUID,
    column_name: str,
    limit_update: WIPLimitUpdate,
    current_user: User = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service)
) -> Any:
    """Update or create manual WIP limit for a column."""
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
    """Validate if moving story violates WIP limits (uses dynamic for InProgress/Review)."""
    try:
        allowed, violation = kanban_service.validate_wip_move(
            project_id=project_id,
            story_id=story_id,
            target_status=target_status
        )
        
        if not allowed:
            return {"allowed": False, "violation": violation}
        elif violation:
            return {"allowed": True, "violation": violation, "warning": True}
        else:
            return {"allowed": True, "violation": None}
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/projects/{project_id}/policies/initialize-defaults")
def initialize_default_policies(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Initialize default workflow policies for a project.
    Creates standard policies for common transitions if they don't exist.
    """
    default_policies = [
        {
            "from_status": "Todo",
            "to_status": "InProgress",
            "criteria": {
                "assignee_required": True,
                "story_points_estimated": True
            },
            "is_active": True
        },
        {
            "from_status": "InProgress",
            "to_status": "Review",
            "criteria": {},
            "is_active": True
        },
        {
            "from_status": "Review",
            "to_status": "Done",
            "criteria": {
                "reviewer_id": True,
                "acceptance_criteria_defined": True
            },
            "is_active": True
        }
    ]

    created_count = 0
    for policy_data in default_policies:
        # Check if policy already exists
        existing = db.exec(
            select(WorkflowPolicy).where(
                and_(
                    WorkflowPolicy.project_id == project_id,
                    WorkflowPolicy.from_status == policy_data["from_status"],
                    WorkflowPolicy.to_status == policy_data["to_status"]
                )
            )
        ).first()

        if not existing:
            new_policy = WorkflowPolicy(
                project_id=project_id,
                from_status=policy_data["from_status"],
                to_status=policy_data["to_status"],
                criteria=policy_data["criteria"],
                is_active=policy_data["is_active"]
            )
            db.add(new_policy)
            created_count += 1

    db.commit()
    return {"message": f"Initialized {created_count} default policies", "created": created_count}


@router.get("/projects/{project_id}/policies", response_model=WorkflowPoliciesPublic)
def get_workflow_policies(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get all workflow policies for a project"""
    policies = db.exec(
        select(WorkflowPolicy).where(WorkflowPolicy.project_id == project_id)
    ).all()

    return WorkflowPoliciesPublic(data=policies, count=len(policies))


@router.put("/projects/{project_id}/policies/{from_status}/{to_status}", response_model=WorkflowPolicyPublic)
def update_workflow_policy(
    project_id: UUID,
    from_status: str,
    to_status: str,
    policy_update: WorkflowPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Update or create workflow policy"""
    # Try to find existing policy
    existing_policy = db.exec(
        select(WorkflowPolicy).where(
            and_(
                WorkflowPolicy.project_id == project_id,
                WorkflowPolicy.from_status == from_status,
                WorkflowPolicy.to_status == to_status
            )
        )
    ).first()

    if existing_policy:
        # Update existing
        if policy_update.criteria is not None:
            existing_policy.criteria = policy_update.criteria
        if policy_update.required_role is not None:
            existing_policy.required_role = policy_update.required_role
        if policy_update.is_active is not None:
            existing_policy.is_active = policy_update.is_active
        existing_policy.updated_at = datetime.now(timezone.utc)
        db.add(existing_policy)
        db.commit()
        db.refresh(existing_policy)
        return existing_policy
    else:
        # Create new
        new_policy = WorkflowPolicy(
            project_id=project_id,
            from_status=from_status,
            to_status=to_status,
            criteria=policy_update.criteria,
            required_role=policy_update.required_role,
            is_active=policy_update.is_active if policy_update.is_active is not None else True
        )
        db.add(new_policy)
        db.commit()
        db.refresh(new_policy)
        return new_policy


@router.post("/projects/{project_id}/stories/{story_id}/validate-policy")
def validate_policy_before_move(
    project_id: UUID,
    story_id: UUID,
    from_status: str,
    to_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Validate if a story transition meets workflow policy criteria.
    Returns {"allowed": true/false, "violations": [...]}
    """
    # Get the story
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Get workflow policy
    policy = db.exec(
        select(WorkflowPolicy).where(
            and_(
                WorkflowPolicy.project_id == project_id,
                WorkflowPolicy.from_status == from_status,
                WorkflowPolicy.to_status == to_status,
                WorkflowPolicy.is_active == True
            )
        )
    ).first()

    if not policy or not policy.criteria:
        # No policy or criteria, allow
        return {"allowed": True, "violations": []}

    violations = []

    # Check criteria
    criteria = policy.criteria

    if criteria.get("assignee_required") and not story.assignee_id:
        violations.append("Story must have an assignee")

    if criteria.get("acceptance_criteria_defined") and not story.acceptance_criteria:
        violations.append("Acceptance criteria must be defined")

    if criteria.get("story_points_estimated") and not story.story_point:
        violations.append("Story points must be estimated")

    # If there are violations, block the move
    if violations:
        return {"allowed": False, "violations": violations}

    return {"allowed": True, "violations": []}


@router.get("/projects/{project_id}/flow-metrics", response_model=ProjectFlowMetrics)
def get_project_flow_metrics(
    project_id: UUID,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service)
) -> Any:
    """Get aggregated flow metrics for a project"""
    metrics = kanban_service.get_project_flow_metrics(project_id)
    
    return ProjectFlowMetrics(
        avg_cycle_time_hours=metrics["avg_cycle_time_hours"],
        avg_lead_time_hours=metrics["avg_lead_time_hours"],
        throughput_per_week=metrics["throughput_per_week"],
        total_completed=metrics["total_completed"],
        work_in_progress=metrics["work_in_progress"],
        aging_items=metrics["aging_items"],
        bottlenecks=metrics["bottlenecks"]
    )


@router.get("/stories/{story_id}/flow-metrics", response_model=StoryFlowMetrics)
def get_story_flow_metrics(
    story_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get flow metrics for a specific story"""
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return StoryFlowMetrics(
        id=story.id,
        title=story.title,
        status=story.status.value,
        created_at=story.created_at,
        started_at=story.started_at,
        review_started_at=story.review_started_at,
        testing_started_at=story.testing_started_at,
        completed_at=story.completed_at,
        cycle_time_hours=story.cycle_time_hours,
        lead_time_hours=story.lead_time_hours,
        age_in_current_status_hours=story.age_in_current_status_hours
    )
