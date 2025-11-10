"""CRUD operations for ProjectRules model."""

from uuid import UUID
from typing import Optional
from sqlmodel import Session, select
from app.models import ProjectRules
from app.schemas import ProjectRulesCreate, ProjectRulesUpdate


def create_project_rules(
    *,
    session: Session,
    rules_in: ProjectRulesCreate,
) -> ProjectRules:
    """Create project rules."""
    db_rules = ProjectRules.model_validate(rules_in)
    session.add(db_rules)
    session.commit()
    session.refresh(db_rules)
    return db_rules


def get_project_rules(
    *,
    session: Session,
    project_id: UUID,
) -> Optional[ProjectRules]:
    """Get project rules by project_id."""
    statement = select(ProjectRules).where(ProjectRules.project_id == project_id)
    return session.exec(statement).first()


def update_project_rules(
    *,
    session: Session,
    db_rules: ProjectRules,
    rules_in: ProjectRulesUpdate,
) -> ProjectRules:
    """Update project rules."""
    rules_data = rules_in.model_dump(exclude_unset=True)
    db_rules.sqlmodel_update(rules_data)
    session.add(db_rules)
    session.commit()
    session.refresh(db_rules)
    return db_rules
