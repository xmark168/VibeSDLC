"""
User management endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserUpdatePassword
from app.services.user import UserService
from app.services.auth import AuthService, get_current_user
from app.models.user import User
from app.core.exceptions import ValidationException, NotFoundException, ConflictException

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user account.
    """
    try:
        # Validate passwords match
        user_create.validate_passwords_match()

        user_service = UserService(db)
        user = await user_service.create_user(user_create)
        return user
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile.
    """
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(current_user.id, user_update)
        return updated_user
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.put("/me/password")
async def update_current_user_password(
    password_update: UserUpdatePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's password.
    """
    try:
        # Validate passwords match
        password_update.validate_passwords_match()

        user_service = UserService(db)
        await user_service.update_user_password(
            user_id=current_user.id,
            current_password=password_update.current_password,
            new_password=password_update.new_password
        )
        return {"message": "Password updated successfully"}
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user by ID (requires authentication).
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        return user
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of users (requires authentication).
    """
    user_service = UserService(db)
    users = await user_service.get_users(skip=skip, limit=limit)
    return users

@router.post("/test", status_code=status.HTTP_200_OK)
async def trigger_test_feature(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger the test feature for the Developer Agent.
    """
    # Implement the logic to trigger the test feature here
    return {"message": "Test feature triggered successfully"}