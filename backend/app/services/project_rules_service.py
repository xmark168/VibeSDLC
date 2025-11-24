"""Project Rules Service - Encapsulates project rules business logic."""

from uuid import UUID
from typing import Optional

from sqlmodel import Session, select

from app.models import ProjectRules
from app.schemas import ProjectRulesCreate, ProjectRulesUpdate


class ProjectRulesService:
    """Service for project rules management."""

    def __init__(self, session: Session):
        self.session = session

    # ===== CRUD Operations =====

    def create(self, rules_in: ProjectRulesCreate) -> ProjectRules:
        """Create project rules."""
        db_rules = ProjectRules.model_validate(rules_in)
        self.session.add(db_rules)
        self.session.commit()
        self.session.refresh(db_rules)
        return db_rules

    def get_by_project(self, project_id: UUID) -> Optional[ProjectRules]:
        """Get project rules by project_id."""
        statement = select(ProjectRules).where(ProjectRules.project_id == project_id)
        return self.session.exec(statement).first()

    def update(self, db_rules: ProjectRules, rules_in: ProjectRulesUpdate) -> ProjectRules:
        """Update project rules."""
        rules_data = rules_in.model_dump(exclude_unset=True)
        db_rules.sqlmodel_update(rules_data)
        self.session.add(db_rules)
        self.session.commit()
        self.session.refresh(db_rules)
        return db_rules
