"""Plan Service - Encapsulates all plan-related business logic."""

from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, func, or_, and_, col
from app.models import Plan
from app.schemas.plan import PlanCreate, PlanUpdate


class PlanService:
    """Service for plan management."""

    def __init__(self, session: Session):
        self.session = session

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        tier: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_featured: Optional[bool] = None,
        order_by: str = "sort_index"  # Default sort by sort_index
    ) -> tuple[list[Plan], int]:
        """
        Get all plans with pagination, search, and filters.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            search: Search term for name, code, or description
            tier: Filter by tier (free, pro, standard, enterprise, custom)
            is_active: Filter by active status
            is_featured: Filter by featured status
            order_by: Field to order by (default: sort_index)

        Returns:
            Tuple of (list of plans, total count)
        """
        # Build base query with filters
        conditions = []

        # Search filter - search in name, code, or description
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    col(Plan.name).ilike(search_term),
                    col(Plan.code).ilike(search_term),
                    col(Plan.description).ilike(search_term)
                )
            )

        # Tier filter
        if tier:
            conditions.append(Plan.tier == tier)

        # Active status filter
        if is_active is not None:
            conditions.append(Plan.is_active == is_active)

        # Featured filter
        if is_featured is not None:
            conditions.append(Plan.is_featured == is_featured)

        # Count total records with filters
        count_statement = select(func.count(Plan.id))
        if conditions:
            count_statement = count_statement.where(and_(*conditions))
        total_count = self.session.exec(count_statement).one()

        # Build query for data with filters, pagination, and ordering
        statement = select(Plan)
        if conditions:
            statement = statement.where(and_(*conditions))

        # Add ordering
        if order_by == "sort_index":
            statement = statement.order_by(Plan.sort_index.asc())
        elif order_by == "price":
            # Order by monthly_price, with nulls last, fall back to yearly_price
            statement = statement.order_by(func.coalesce(Plan.monthly_price, Plan.yearly_price).asc())
        elif order_by == "created_at":
            statement = statement.order_by(Plan.created_at.desc())
        elif order_by == "name":
            statement = statement.order_by(Plan.name.asc())
        else:
            # Default to sort_index
            statement = statement.order_by(Plan.sort_index.asc())

        # Add pagination
        statement = statement.offset(skip).limit(limit)

        plans = self.session.exec(statement).all()
        return list(plans), total_count

    def get_by_id(self, plan_id: UUID) -> Plan | None:
        """Get plan by ID."""
        return self.session.get(Plan, plan_id)

    def get_by_code(self, code: str) -> Plan | None:
        """Get plan by code."""
        statement = select(Plan).where(Plan.code == code)
        return self.session.exec(statement).first()

    def create(self, plan_in: PlanCreate) -> Plan:
        """Create a new plan."""
        db_obj = Plan.model_validate(plan_in)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def update(self, db_plan: Plan, plan_in: PlanUpdate) -> Plan:
        """Update plan information."""
        plan_data = plan_in.model_dump(exclude_unset=True)
        db_plan.sqlmodel_update(plan_data)
        self.session.add(db_plan)
        self.session.commit()
        self.session.refresh(db_plan)
        return db_plan

    def delete(self, plan_id: UUID) -> bool:
        """
        Delete a plan.

        Returns:
            True if plan was deleted, False if not found
        """
        plan = self.get_by_id(plan_id)
        if not plan:
            return False
        self.session.delete(plan)
        self.session.commit()
        return True

    def get_active_plans(self, skip: int = 0, limit: int = 100) -> tuple[list[Plan], int]:
        """
        Get all active plans ordered by sort_index.
        Convenience method for public-facing plan listings.
        """
        return self.get_all(
            skip=skip,
            limit=limit,
            is_active=True,
            order_by="sort_index"
        )

    def get_featured_plans(self) -> list[Plan]:
        """Get all featured active plans."""
        statement = (
            select(Plan)
            .where(Plan.is_active == True)
            .where(Plan.is_featured == True)
            .order_by(Plan.sort_index.asc())
        )
        return list(self.session.exec(statement).all())
