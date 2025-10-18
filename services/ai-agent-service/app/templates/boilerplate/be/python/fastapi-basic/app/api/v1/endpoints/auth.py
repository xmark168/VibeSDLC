"""
Authentication endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import UserLogin, UserToken, UserTokenRefresh
from app.services.auth import AuthService
from app.core.exceptions import AuthenticationException

router = APIRouter()
security = HTTPBearer()


@router.post("/login", response_model=UserToken)
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    User login endpoint.

    Returns access and refresh tokens for valid credentials.
    """
    try:
        auth_service = AuthService(db)
        tokens = await auth_service.authenticate_user(
            email=user_login.email, password=user_login.password
        )
        return tokens
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=UserToken)
async def refresh_token(
    token_refresh: UserTokenRefresh, db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        auth_service = AuthService(db)
        tokens = await auth_service.refresh_access_token(
            refresh_token=token_refresh.refresh_token
        )
        return tokens
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
async def logout(token: str = Depends(security), db: AsyncSession = Depends(get_db)):
    """
    User logout endpoint.

    Invalidates the current access token.
    """
    try:
        auth_service = AuthService(db)
        await auth_service.logout_user(token.credentials)
        return {"message": "Successfully logged out"}
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.post("/verify-token")
async def verify_token(
    token: str = Depends(security), db: AsyncSession = Depends(get_db)
):
    """
    Verify if the provided token is valid.
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(token.credentials)
        return {"valid": True, "user_id": user.id, "email": user.email}
    except AuthenticationException:
        return {"valid": False}
