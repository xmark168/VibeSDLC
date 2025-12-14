import uuid
from uuid import UUID
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import func, select, or_

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
    UpdateAutoRenew,
    UserAdminPublic,
    UsersAdminPublic,
    UserAdminCreate,
    UserAdminUpdate,
    BulkUserIds,
    UserStatsResponse,
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


def user_to_admin_public(user: User) -> UserAdminPublic:
    """
    Convert User model to UserAdminPublic schema with extended info.

    Args:
        user: User model instance

    Returns:
        UserAdminPublic schema
    """
    return UserAdminPublic(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        is_locked=user.is_locked,
        locked_until=user.locked_until,
        failed_login_attempts=user.failed_login_attempts,
        login_provider=user.login_provider,
        balance=user.balance or 0.0,
        created_at=user.created_at,
        updated_at=user.updated_at,
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
    # Query active subscription for current user (including FREE plan with no end_at)
    now = datetime.now(timezone.utc)
    subscription_statement = (
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == "active")
        .where(or_(Subscription.end_at > now, Subscription.end_at == None))
    )
    subscription = session.exec(subscription_statement).first()

    if not subscription:
        # No active subscription - auto-assign FREE plan for old users
        free_plan_statement = select(Plan).where(Plan.code == "FREE")
        free_plan = session.exec(free_plan_statement).first()

        if not free_plan:
            # If no FREE plan exists, return null
            return UserSubscriptionResponse(
                subscription=None,
                credit_wallet=None
            )

        # Auto-create subscription and wallet for existing users without one
        subscription = Subscription(
            user_id=current_user.id,
            plan_id=free_plan.id,
            status="active",
            start_at=datetime.now(timezone.utc),
            end_at=None,
            auto_renew=False,
        )
        session.add(subscription)
        session.flush()
        
        wallet = CreditWallet(
            user_id=current_user.id,
            wallet_type="subscription",
            subscription_id=subscription.id,
            period_start=datetime.now(timezone.utc),
            period_end=None,
            total_credits=free_plan.monthly_credits or 100,
            used_credits=0,
        )
        session.add(wallet)
        session.commit()
        session.refresh(subscription)
        session.refresh(wallet)

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


@router.post("/me/subscription/cancel")
def cancel_current_subscription(
    *,
    session: SessionDep,
    current_user: CurrentUser
) -> Message:
    """
    Cancel current user's active subscription
    """
    # Get active subscription
    now = datetime.now(timezone.utc)
    subscription_statement = (
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == "active")
        .where(Subscription.end_at > now)
    )
    subscription = session.exec(subscription_statement).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    # Update subscription status to canceled
    subscription.status = "canceled"
    subscription.auto_renew = False  # Disable auto-renew when canceling
    session.add(subscription)
    session.commit()

    return Message(message="Subscription canceled successfully. Your plan will remain active until the end of the current billing period.")


@router.put("/me/subscription/auto-renew")
def update_auto_renew(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    auto_renew_data: UpdateAutoRenew
) -> Message:
    """
    Update auto-renew setting for current user's subscription
    """
    # Get active subscription
    now = datetime.now(timezone.utc)
    subscription_statement = (
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == "active")
        .where(Subscription.end_at > now)
    )
    subscription = session.exec(subscription_statement).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    # Update auto-renew setting
    subscription.auto_renew = auto_renew_data.auto_renew
    session.add(subscription)
    session.commit()

    status_text = "enabled" if auto_renew_data.auto_renew else "disabled"
    return Message(message=f"Auto-renew {status_text} successfully")


# ==================== ADMIN USER MANAGEMENT ENDPOINTS ====================


@router.get(
    "/admin/list",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersAdminPublic,
)
def admin_list_users(
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name, email, or username"),
    role: Optional[str] = Query(None, description="Filter by role (admin, user)"),
    status: Optional[str] = Query(None, description="Filter by status (active, inactive, locked)"),
    order_by: str = Query("created_at", description="Order by field"),
    order_dir: str = Query("desc", description="Order direction (asc, desc)"),
) -> Any:
    """
    Admin endpoint: List all users with extended information and filters.
    """
    # Build base query
    statement = select(User)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        statement = statement.where(
            or_(
                User.email.ilike(search_term),
                User.username.ilike(search_term),
                User.full_name.ilike(search_term),
            )
        )

    # Apply role filter
    if role:
        if role.lower() == "admin":
            statement = statement.where(User.role == Role.ADMIN)
        elif role.lower() == "user":
            statement = statement.where(User.role == Role.USER)

    # Apply status filter
    if status:
        if status.lower() == "active":
            statement = statement.where(User.is_active == True, User.is_locked == False)
        elif status.lower() == "inactive":
            statement = statement.where(User.is_active == False)
        elif status.lower() == "locked":
            statement = statement.where(User.is_locked == True)

    # Get total count before pagination
    count_statement = select(func.count()).select_from(statement.subquery())
    count = session.exec(count_statement).one()

    # Apply ordering
    order_column = getattr(User, order_by, User.created_at)
    if order_dir.lower() == "desc":
        statement = statement.order_by(order_column.desc())
    else:
        statement = statement.order_by(order_column.asc())

    # Apply pagination
    statement = statement.offset(skip).limit(limit)
    users = session.exec(statement).all()

    # Convert to admin public schema
    users_public = [user_to_admin_public(user) for user in users]

    return UsersAdminPublic(data=users_public, count=count)


@router.get(
    "/admin/stats",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserStatsResponse,
)
def admin_get_user_stats(session: SessionDep) -> Any:
    """
    Admin endpoint: Get user statistics for dashboard.
    """
    total_users = session.exec(select(func.count()).select_from(User)).one()
    active_users = session.exec(
        select(func.count()).select_from(User).where(User.is_active == True, User.is_locked == False)
    ).one()
    inactive_users = session.exec(
        select(func.count()).select_from(User).where(User.is_active == False)
    ).one()
    locked_users = session.exec(
        select(func.count()).select_from(User).where(User.is_locked == True)
    ).one()
    admin_users = session.exec(
        select(func.count()).select_from(User).where(User.role == Role.ADMIN)
    ).one()
    regular_users = session.exec(
        select(func.count()).select_from(User).where(User.role == Role.USER)
    ).one()
    users_with_oauth = session.exec(
        select(func.count()).select_from(User).where(User.login_provider != None)
    ).one()

    return UserStatsResponse(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        locked_users=locked_users,
        admin_users=admin_users,
        regular_users=regular_users,
        users_with_oauth=users_with_oauth,
    )


@router.post(
    "/admin/create",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserAdminPublic,
)
def admin_create_user(*, session: SessionDep, user_in: UserAdminCreate) -> Any:
    """
    Admin endpoint: Create new user with full control over all fields.
    """
    user_service = UserService(session)
    existing_user = user_service.get_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists.",
        )

    # Create user with all admin-controlled fields
    db_user = User(
        username=user_in.username,
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return user_to_admin_public(db_user)


# IMPORTANT: Bulk routes must come BEFORE dynamic {user_id} routes
@router.post(
    "/admin/bulk/lock",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def admin_bulk_lock_users(
    *,
    session: SessionDep,
    bulk_data: BulkUserIds,
    current_user: CurrentUser,
) -> Message:
    """
    Admin endpoint: Lock multiple user accounts at once.
    """
    locked_count = 0
    skipped_count = 0

    for user_id in bulk_data.user_ids:
        # Skip self
        if user_id == current_user.id:
            skipped_count += 1
            continue

        db_user = session.get(User, user_id)
        if db_user and not db_user.is_locked:
            db_user.is_locked = True
            db_user.locked_until = None
            session.add(db_user)
            locked_count += 1

    session.commit()

    return Message(message=f"Locked {locked_count} users. Skipped {skipped_count} users.")


@router.post(
    "/admin/bulk/unlock",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def admin_bulk_unlock_users(
    *,
    session: SessionDep,
    bulk_data: BulkUserIds,
) -> Message:
    """
    Admin endpoint: Unlock multiple user accounts at once.
    """
    unlocked_count = 0

    for user_id in bulk_data.user_ids:
        db_user = session.get(User, user_id)
        if db_user and db_user.is_locked:
            db_user.is_locked = False
            db_user.locked_until = None
            db_user.failed_login_attempts = 0
            session.add(db_user)
            unlocked_count += 1

    session.commit()

    return Message(message=f"Unlocked {unlocked_count} users")


@router.delete(
    "/admin/bulk",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def admin_bulk_delete_users(
    *,
    session: SessionDep,
    bulk_data: BulkUserIds,
    current_user: CurrentUser,
) -> Message:
    """
    Admin endpoint: Delete multiple users at once.
    """
    deleted_count = 0
    skipped_count = 0

    for user_id in bulk_data.user_ids:
        # Skip self
        if user_id == current_user.id:
            skipped_count += 1
            continue

        db_user = session.get(User, user_id)
        if db_user:
            session.delete(db_user)
            deleted_count += 1

    session.commit()

    return Message(message=f"Deleted {deleted_count} users. Skipped {skipped_count} users.")


# Dynamic {user_id} routes - must come AFTER static/bulk routes
@router.patch(
    "/admin/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserAdminPublic,
)
def admin_update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserAdminUpdate,
    current_user: CurrentUser,
) -> Any:
    """
    Admin endpoint: Update user with full control over all fields including role and status.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from demoting themselves
    if db_user.id == current_user.id and user_in.role == Role.USER:
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own role from admin to user",
        )

    # Check email uniqueness if changing
    if user_in.email and user_in.email != db_user.email:
        user_service = UserService(session)
        existing_user = user_service.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="A user with this email already exists",
            )

    # Update fields
    update_data = user_in.model_dump(exclude_unset=True)

    # Handle password separately
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    elif "password" in update_data:
        del update_data["password"]

    for field, value in update_data.items():
        setattr(db_user, field, value)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return user_to_admin_public(db_user)


@router.post(
    "/admin/{user_id}/lock",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def admin_lock_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    current_user: CurrentUser,
) -> Message:
    """
    Admin endpoint: Lock a user account.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot lock your own account")

    db_user.is_locked = True
    db_user.locked_until = None  # Indefinite lock by admin
    session.add(db_user)
    session.commit()

    return Message(message=f"User {db_user.email} has been locked")


@router.post(
    "/admin/{user_id}/unlock",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def admin_unlock_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
) -> Message:
    """
    Admin endpoint: Unlock a user account.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_locked = False
    db_user.locked_until = None
    db_user.failed_login_attempts = 0
    session.add(db_user)
    session.commit()

    return Message(message=f"User {db_user.email} has been unlocked")


@router.post(
    "/admin/{user_id}/revoke-sessions",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def admin_revoke_user_sessions(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
) -> Message:
    """
    Admin endpoint: Revoke all sessions/tokens for a user.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_service = UserService(session)
    user_service.revoke_all_user_tokens(user_id)

    return Message(message=f"All sessions for {db_user.email} have been revoked")
