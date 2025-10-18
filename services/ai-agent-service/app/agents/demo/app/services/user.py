"""
User service for user management operations.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth import AuthService
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.auth_service = AuthService(db)

    async def create_user(self, user_create: UserCreate) -> User:
        """Create a new user."""

        # Check if user already exists
        existing_user = await self.get_user_by_email(user_create.email)
        if existing_user:
            raise ConflictException("User with this email already exists")

        existing_username = await self.get_user_by_username(user_create.username)
        if existing_username:
            raise ConflictException("User with this username already exists")

        # Create new user
        hashed_password = self.auth_service.get_password_hash(user_create.password)

        db_user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            bio=user_create.bio,
            avatar_url=user_create.avatar_url,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            is_superuser=False,
        )

        try:
            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)
            return db_user
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException("User with this email or username already exists")

    async def get_user_by_id(self, user_id: int) -> User:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")

        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get list of users with pagination."""
        result = await self.db.execute(
            select(User).where(User.is_active == True).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        """Update user profile."""
        user = await self.get_user_by_id(user_id)

        # Update fields
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException("Update failed due to constraint violation")

    async def update_user_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> None:
        """Update user password."""
        user = await self.get_user_by_id(user_id)

        # Verify current password
        if not self.auth_service.verify_password(
            current_password, user.hashed_password
        ):
            raise ValidationException("Current password is incorrect")

        # Update password
        user.hashed_password = self.auth_service.get_password_hash(new_password)

        await self.db.commit()

    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate user account."""
        user = await self.get_user_by_id(user_id)
        user.is_active = False

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def activate_user(self, user_id: int) -> User:
        """Activate user account."""
        user = await self.get_user_by_id(user_id)
        user.is_active = True

        await self.db.commit()
        await self.db.refresh(user)
        return user
