import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.services import UserService
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import User, Role, Subscription, CreditWallet, Plan
from app.schemas import (
    Message,
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
    SubscriptionPublic,
    CreditWalletPublic,
    UserSubscriptionResponse,
)
from datetime import datetime, timezone

router = APIRouter(prefix="/users", tags=["users"])


def user_to_public(user: User) -> UserPublic:
    """
    Convert User model to UserPublic schema.

    Args:
        user: User model instance

    Returns:
        UserPublic schema
    """
    return UserPublic(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
    )


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = select(User).offset(skip).limit(limit)
    users = session.exec(statement).all()

    # Convert to UserPublic
    users_public = [user_to_public(user) for user in users]

    return UsersPublic(data=users_public, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user_service = UserService(session)
    user = user_service.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = user_service.create(user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

    session.refresh(user)
    return user_to_public(user)


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        user_service = UserService(session)
        existing_user = user_service.get_by_email(user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return user_to_public(current_user)


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    session.refresh(current_user)
    return user_to_public(current_user)


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.role == Role.ADMIN:
        raise HTTPException(
            status_code=403, detail="Admin users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user_service = UserService(session)
    user = user_service.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = user_service.create(user_create)

    session.refresh(user)
    return user_to_public(user)


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id with GitHub installation data.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id != current_user.id and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )

    session.refresh(user)
    return user_to_public(user)


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        user_service = UserService(session)
        existing_user = user_service.get_by_email(user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    user_service = UserService(session)
    db_user = user_service.update(db_user, user_in)

    session.refresh(db_user)
    return user_to_public(db_user)


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    # Note: User deletion will cascade to related entities via foreign key constraints
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")


@router.get("/me/subscription", response_model=UserSubscriptionResponse)
def get_current_user_subscription(
    *,
    session: SessionDep,
    current_user: CurrentUser
) -> UserSubscriptionResponse:
    """
    Get current user's active subscription with plan details and credit wallet
    """
    # Query active subscription for current user
    now = datetime.now(timezone.utc)
    subscription_statement = (
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == "active")
        .where(Subscription.end_at > now)
    )
    subscription = session.exec(subscription_statement).first()

    if not subscription:
        # No active subscription - user is on FREE plan
        return UserSubscriptionResponse(
            subscription=None,
            credit_wallet=None
        )

    # Get plan details
    plan = session.get(Plan, subscription.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Get credit wallet for this subscription
    wallet_statement = (
        select(CreditWallet)
        .where(CreditWallet.subscription_id == subscription.id)
        .where(CreditWallet.user_id == current_user.id)
    )
    wallet = session.exec(wallet_statement).first()

    # Build subscription response
    from app.schemas.plan import PlanPublic
    plan_public = PlanPublic(
        id=plan.id,
        name=plan.name,
        code=plan.code,
        description=plan.description,
        monthly_price=plan.monthly_price,
        yearly_price=plan.yearly_price,
        currency=plan.currency,
        monthly_credits=plan.monthly_credits,
        available_project=plan.available_project,
        additional_credit_price=plan.additional_credit_price,
        is_active=plan.is_active,
        is_featured=plan.is_featured,
        is_custom_price=plan.is_custom_price,
        yearly_discount_percentage=plan.yearly_discount_percentage,
        sort_index=plan.sort_index,
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )

    subscription_public = SubscriptionPublic(
        id=subscription.id,
        status=subscription.status,
        start_at=subscription.start_at,
        end_at=subscription.end_at,
        auto_renew=subscription.auto_renew,
        plan=plan_public
    )

    # Build wallet response if exists
    wallet_public = None
    if wallet:
        remaining_credits = wallet.total_credits - wallet.used_credits
        wallet_public = CreditWalletPublic(
            id=wallet.id,
            total_credits=wallet.total_credits,
            used_credits=wallet.used_credits,
            remaining_credits=remaining_credits,
            period_start=wallet.period_start,
            period_end=wallet.period_end
        )

    return UserSubscriptionResponse(
        subscription=subscription_public,
        credit_wallet=wallet_public
    )
