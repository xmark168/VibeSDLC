"""API routes for ProjectRules management."""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser, SessionDep
from app.models import Project
from app.schemas import ProjectRulesCreate, ProjectRulesUpdate, ProjectRulesPublic
from app.crud import project_rules as crud_rules

router = APIRouter(prefix="/project-rules", tags=["project-rules"])


@router.post("/", response_model=ProjectRulesPublic)
def create_project_rules(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    rules_in: ProjectRulesCreate,
) -> ProjectRulesPublic:
    """Create project rules."""
    # Validate project exists
    project = session.get(Project, rules_in.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if rules already exist
    existing_rules = crud_rules.get_project_rules(
        session=session,
        project_id=rules_in.project_id,
    )
    if existing_rules:
        raise HTTPException(status_code=400, detail="Project rules already exist")

    rules = crud_rules.create_project_rules(session=session, rules_in=rules_in)
    return ProjectRulesPublic.model_validate(rules)


@router.get("/{project_id}", response_model=ProjectRulesPublic)
def get_project_rules(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID,
) -> ProjectRulesPublic:
    """Get project rules by project_id."""
    rules = crud_rules.get_project_rules(session=session, project_id=project_id)
    if not rules:
        raise HTTPException(status_code=404, detail="Project rules not found")
    return ProjectRulesPublic.model_validate(rules)


@router.put("/{project_id}", response_model=ProjectRulesPublic)
def update_project_rules(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID,
    rules_in: ProjectRulesUpdate,
) -> ProjectRulesPublic:
    """Update project rules."""
    db_rules = crud_rules.get_project_rules(session=session, project_id=project_id)
    if not db_rules:
        raise HTTPException(status_code=404, detail="Project rules not found")

    rules = crud_rules.update_project_rules(
        session=session,
        db_rules=db_rules,
        rules_in=rules_in,
    )
    return ProjectRulesPublic.model_validate(rules)
