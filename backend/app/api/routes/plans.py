"""Plans API - Endpoints for managing subscription plans."""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.services.plan_service import PlanService
from app.models import Plan
from app.schemas.plan import (
    PlanCreate,
    PlanPublic,
    PlansPublic,
    PlanUpdate,
)
from app.schemas.auth import Message

router = APIRouter(prefix="/plans", tags=["plans"])


def plan_to_public(plan: Plan) -> PlanPublic:
    """
    Convert Plan model to PlanPublic schema.

    Args:
        plan: Plan model instance

    Returns:
        PlanPublic schema
    """
    return PlanPublic(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        description=plan.description,
        monthly_price=plan.monthly_price,
        yearly_price=plan.yearly_price,
        yearly_discount_percentage=plan.yearly_discount_percentage,
        currency=plan.currency,
        monthly_credits=plan.monthly_credits,
        additional_credit_price=plan.additional_credit_price,
        available_project=plan.available_project,
        is_active=plan.is_active,
        tier=plan.tier,
        sort_index=plan.sort_index,
        is_featured=plan.is_featured,
        is_custom_price=plan.is_custom_price,
        features_text=plan.features_text,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("/", response_model=PlansPublic)
def list_plans(
    session: SessionDep,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search term for name, code, or description"),
    tier: Optional[str] = Query(None, description="Filter by tier (free, pro, standard, enterprise, custom)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    order_by: str = Query("sort_index", description="Field to order by (sort_index, price, created_at, name)"),
) -> Any:
    """
    Retrieve plans with pagination, search, and filters.

    Public endpoint - no authentication required.
    """
    plan_service = PlanService(session)
    plans, total_count = plan_service.get_all(
        skip=skip,
        limit=limit,
        search=search,
        tier=tier,
        is_active=is_active,
        is_featured=is_featured,
        order_by=order_by,
    )

    # Convert to PlanPublic
    plans_public = [plan_to_public(plan) for plan in plans]

    return PlansPublic(data=plans_public, count=total_count)


@router.get("/featured", response_model=list[PlanPublic])
def get_featured_plans(session: SessionDep) -> Any:
    """
    Get all featured plans.

    Public endpoint - no authentication required.
    Returns plans sorted by sort_index.
    """
    plan_service = PlanService(session)
    plans = plan_service.get_featured_plans()
    return [plan_to_public(plan) for plan in plans]


@router.get("/{plan_id}", response_model=PlanPublic)
def get_plan_by_id(
    plan_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """
    Get a specific plan by ID.

    Public endpoint - no authentication required.
    """
    plan_service = PlanService(session)
    plan = plan_service.get_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return plan_to_public(plan)


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=PlanPublic,
)
def create_plan(
    *,
    session: SessionDep,
    plan_in: PlanCreate,
) -> Any:
    """
    Create new plan.

    Admin only endpoint.
    """
    plan_service = PlanService(session)

    # Check if plan with same code already exists
    existing_plan = plan_service.get_by_code(plan_in.code)
    if existing_plan:
        raise HTTPException(
            status_code=400,
            detail="A plan with this code already exists in the system.",
        )

    plan = plan_service.create(plan_in)
    return plan_to_public(plan)


@router.patch(
    "/{plan_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=PlanPublic,
)
def update_plan(
    *,
    session: SessionDep,
    plan_id: uuid.UUID,
    plan_in: PlanUpdate,
) -> Any:
    """
    Update a plan.

    Admin only endpoint.
    """
    plan_service = PlanService(session)
    db_plan = plan_service.get_by_id(plan_id)
    if not db_plan:
        raise HTTPException(
            status_code=404,
            detail="The plan with this id does not exist in the system",
        )

    # If updating code, check for duplicates
    if plan_in.code and plan_in.code != db_plan.code:
        existing_plan = plan_service.get_by_code(plan_in.code)
        if existing_plan:
            raise HTTPException(
                status_code=409,
                detail="A plan with this code already exists"
            )

    # Validate pricing logic when updating
    # Get the final monthly price and discount percentage after the update
    final_monthly = plan_in.monthly_price if plan_in.monthly_price is not None else db_plan.monthly_price
    final_discount = plan_in.yearly_discount_percentage if plan_in.yearly_discount_percentage is not None else db_plan.yearly_discount_percentage

    # Validate discount percentage is between 0 and 100
    if final_discount is not None:
        if final_discount < 0 or final_discount > 100:
            raise HTTPException(
                status_code=400,
                detail="Yearly discount percentage must be between 0 and 100"
            )

    updated_plan = plan_service.update(db_plan, plan_in)
    return plan_to_public(updated_plan)


@router.delete(
    "/{plan_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def delete_plan(
    session: SessionDep,
    plan_id: uuid.UUID,
) -> Any:
    """
    Delete a plan.

    Admin only endpoint.
    Note: Plan deletion will cascade to related subscriptions via foreign key constraints.
    """
    plan_service = PlanService(session)
    plan = plan_service.get_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check if plan has active subscriptions
    if plan.plan_subscriptions:
        active_subscriptions = [sub for sub in plan.plan_subscriptions if sub.status == "active"]
        if active_subscriptions:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete plan with {len(active_subscriptions)} active subscription(s). Please deactivate the plan instead."
            )

    plan_service.delete(plan_id)
    return Message(message="Plan deleted successfully")
