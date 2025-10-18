"""
Authentication service for user login, token management, and security.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserToken
from app.core.exceptions import AuthenticationException

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
security = HTTPBearer()


class AuthService:
    """Authentication service for user management and JWT tokens."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return pwd_context.hash(password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def authenticate_user(self, email: str, password: str) -> UserToken:
        """Authenticate user and return tokens."""
        user = await self.get_user_by_email(email)

        if not user:
            raise AuthenticationException("Invalid email or password")

        if not user.is_active:
            raise AuthenticationException("Account is deactivated")

        if not self.verify_password(password, user.hashed_password):
            raise AuthenticationException("Invalid email or password")

        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires,
        )

        refresh_token = self.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return UserToken(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> UserToken:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM]
            )
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")

            if user_id is None or token_type != "refresh":
                raise AuthenticationException("Invalid refresh token")

        except JWTError:
            raise AuthenticationException("Invalid refresh token")

        # Get user
        result = await self.db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise AuthenticationException("User not found or inactive")

        # Create new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires,
        )

        new_refresh_token = self.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return UserToken(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_current_user(self, token: str) -> User:
        """Get current user from JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")

            if user_id is None:
                raise AuthenticationException("Invalid token")

        except JWTError:
            raise AuthenticationException("Invalid token")

        result = await self.db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if user is None:
            raise AuthenticationException("User not found")

        if not user.is_active:
            raise AuthenticationException("User account is deactivated")

        return user

    async def logout_user(self, token: str) -> None:
        """Logout user (token invalidation would be implemented with Redis/cache)."""
        # In a production app, you would add the token to a blacklist
        # stored in Redis or similar cache system
        pass


# Dependency to get current user
async def get_current_user(
    token: str = Depends(security), db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI dependency to get current authenticated user."""
    auth_service = AuthService(db)
    try:
        return await auth_service.get_current_user(token.credentials)
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
