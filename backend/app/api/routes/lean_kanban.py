"""
Lean Kanban API endpoints for WIP limits, workflow policies, and flow metrics.
Implements core Lean Kanban principles.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func, and_
from typing import Any

from app.api.deps import get_current_user, get_db
from app.models import User, Story, StoryStatus, WorkflowPolicy, Project
from app.schemas import (
    WIPLimitCreate, WIPLimitUpdate, WIPLimitPublic, WIPLimitsPublic,
    WorkflowPolicyCreate, WorkflowPolicyUpdate, WorkflowPolicyPublic, WorkflowPoliciesPublic,
    StoryFlowMetrics, ProjectFlowMetrics, WIPViolation
)

router = APIRouter(tags=["lean-kanban"])


# ===== WIP Limits Endpoints =====

@router.get("/projects/{project_id}/wip-limits", response_model=WIPLimitsPublic)
def get_wip_limits(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get all WIP limits for a project from wip_data JSONB column"""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Convert wip_data JSONB to WIPLimit list format
    limits = []
    if project.wip_data:
        for column_name, config in project.wip_data.items():
            limits.append({
                "id": str(project_id),  # Using project_id as id
                "project_id": str(project_id),
                "column_name": column_name,
                "wip_limit": config.get("limit", 10),
                "limit_type": config.get("type", "hard"),
                "created_at": project.created_at,
                "updated_at": project.updated_at
            })

    return WIPLimitsPublic(data=limits, count=len(limits))


@router.put("/projects/{project_id}/wip-limits/{column_name}", response_model=WIPLimitPublic)
def update_wip_limit(
    project_id: UUID,
    column_name: str,
    limit_update: WIPLimitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Update or create WIP limit for a column in wip_data JSONB"""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Initialize wip_data if None
    if project.wip_data is None:
        project.wip_data = {}

    # Update the specific column's WIP limit
    project.wip_data[column_name] = {
        "limit": limit_update.wip_limit,
        "type": limit_update.limit_type or "hard"
    }

    project.updated_at = datetime.now(timezone.utc)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Return response in the expected format
    return {
        "id": str(project_id),
        "project_id": str(project_id),
        "column_name": column_name,
        "wip_limit": limit_update.wip_limit,
        "limit_type": limit_update.limit_type or "hard",
        "created_at": project.created_at,
        "updated_at": project.updated_at
    }


@router.post("/projects/{project_id}/stories/{story_id}/validate-wip")
def validate_wip_before_move(
    project_id: UUID,
    story_id: UUID,
    target_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Validate if moving a story to target status would violate WIP limits.
    Returns {"allowed": true/false, "violation": {...}}
    """
    # Get project and WIP data
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if WIP limit is configured for this column
    if not project.wip_data or target_status not in project.wip_data:
        # No WIP limit configured, allow
        return {"allowed": True, "violation": None}

    wip_config = project.wip_data[target_status]
    wip_limit_value = wip_config.get("limit", 10)
    limit_type = wip_config.get("type", "hard")

    # Count current items in target column (excluding the story being moved)
    current_count = db.exec(
        select(func.count()).select_from(Story).where(
            and_(
                Story.project_id == project_id,
                Story.status == StoryStatus[target_status.upper().replace("PROGRESS", "_PROGRESS")],
                Story.id != story_id
            )
        )
    ).one()

    # Check if adding this story would exceed limit
    new_count = current_count + 1

    if new_count > wip_limit_value:
        # WIP limit exceeded
        violation = WIPViolation(
            column_name=target_status,
            current_count=current_count,
            wip_limit=wip_limit_value,
            limit_type=limit_type,
            message=f"Cannot move to {target_status}: WIP limit {wip_limit_value} exceeded (current: {current_count})"
        )

        # For hard limits, block the move
        if limit_type == "hard":
            return {"allowed": False, "violation": violation.model_dump()}
        else:
            # Soft limit: allow but warn
            return {"allowed": True, "violation": violation.model_dump(), "warning": True}

    return {"allowed": True, "violation": None}


# ===== Workflow Policies Endpoints =====

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


# ===== Flow Metrics Endpoints =====

@router.get("/projects/{project_id}/flow-metrics", response_model=ProjectFlowMetrics)
def get_project_flow_metrics(
    project_id: UUID,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get aggregated flow metrics for a project"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all completed stories in the time range
    completed_stories = db.exec(
        select(Story).where(
            and_(
                Story.project_id == project_id,
                Story.completed_at >= cutoff_date,
                Story.completed_at.isnot(None)
            )
        )
    ).all()

    # Calculate average cycle time and lead time
    cycle_times = [s.cycle_time_hours for s in completed_stories if s.cycle_time_hours is not None]
    lead_times = [s.lead_time_hours for s in completed_stories if s.lead_time_hours is not None]

    avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else None
    avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else None

    # Calculate throughput (stories per week)
    throughput = (len(completed_stories) / days) * 7 if days > 0 else 0

    # Get current WIP
    wip_count = db.exec(
        select(func.count()).select_from(Story).where(
            and_(
                Story.project_id == project_id,
                Story.status.in_([StoryStatus.IN_PROGRESS, StoryStatus.REVIEW])
            )
        )
    ).one()

    # Get aging items (in current status > 3 days)
    aging_threshold_hours = 72  # 3 days
    all_wip_stories = db.exec(
        select(Story).where(
            and_(
                Story.project_id == project_id,
                Story.status != StoryStatus.DONE
            )
        )
    ).all()

    aging_items = [
        {
            "id": str(s.id),
            "title": s.title,
            "status": s.status.value,
            "age_hours": s.age_in_current_status_hours
        }
        for s in all_wip_stories
        if s.age_in_current_status_hours > aging_threshold_hours
    ]

    # Bottleneck analysis (column with highest avg age)
    column_ages = {}
    for status in [StoryStatus.TODO, StoryStatus.IN_PROGRESS, StoryStatus.REVIEW]:
        column_stories = [s for s in all_wip_stories if s.status == status]
        if column_stories:
            avg_age = sum(s.age_in_current_status_hours for s in column_stories) / len(column_stories)
            column_ages[status.value] = {
                "avg_age_hours": avg_age,
                "count": len(column_stories)
            }

    return ProjectFlowMetrics(
        avg_cycle_time_hours=avg_cycle_time,
        avg_lead_time_hours=avg_lead_time,
        throughput_per_week=throughput,
        total_completed=len(completed_stories),
        work_in_progress=wip_count,
        aging_items=aging_items,
        bottlenecks=column_ages
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
