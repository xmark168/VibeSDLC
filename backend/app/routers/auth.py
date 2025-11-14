from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    MessageResponse,
    UserResponse
)
from app.services.auth_service import AuthService
from app.models import RefreshToken
from app.core.security import verify_refresh_token, create_csrf_token, verify_csrf_token
from app.core.config import settings
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_device_fingerprint(x_device_fingerprint: str = Header(None)) -> str:
    """Extract device fingerprint from header"""
    return x_device_fingerprint or "unknown"

def get_client_ip(request: Request) -> str:
    """Extract client IP address"""
    return request.client.host if request.client else "unknown"

def set_refresh_token_cookie(response: Response, refresh_token: str):
    """Set refresh token as httpOnly cookie"""
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # Convert days to seconds
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=max_age,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )

def clear_refresh_token_cookie(response: Response):
    """Clear refresh token cookie"""
    response.delete_cookie(
        key="refresh_token",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )

def get_csrf_header(x_csrf_token: str = Header(None, alias="X-CSRF-Token")) -> Optional[str]:
    """Extract CSRF token from header"""
    return x_csrf_token

def validate_csrf_token(csrf_token: Optional[str] = Depends(get_csrf_header)):
    """Validate CSRF token for state-changing operations"""
    if not csrf_token or not verify_csrf_token(csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token"
        )

@router.get("/csrf-token")
async def get_csrf_token():
    """
    Lấy CSRF token để sử dụng cho các request state-changing
    Frontend cần gọi endpoint này để lấy CSRF token khi khởi động ứng dụng
    """
    token = create_csrf_token()
    return {"csrf_token": token}

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    response: Response,
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
    device_fingerprint: str = Depends(get_device_fingerprint),
    ip: str = Depends(get_client_ip)
):
    """
    Đăng ký tài khoản mới
    Returns: Token response và thông tin user
    """
    token_response, user = await AuthService.register(data, device_fingerprint, ip, db)

    # Set refresh token as httpOnly cookie
    set_refresh_token_cookie(response, token_response.refresh_token)

    return {
        "message": "User registered successfully",
        "tokens": {
            "access_token": token_response.access_token,
            "token_type": token_response.token_type,
            "expires_in": token_response.expires_in
        },
        "user": UserResponse.model_validate(user)
    }

@router.post("/login")
async def login(
    response: Response,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
    device_fingerprint: str = Depends(get_device_fingerprint),
    ip: str = Depends(get_client_ip)
):
    """
    Đăng nhập

    - **username_or_email**: Username hoặc email
    - **password**: Mật khẩu

    Returns: Access token (refresh token set as httpOnly cookie)
    """
    result = await AuthService.login(data, device_fingerprint, ip, db)

    # Nếu cần 2FA, trả về message khác
    if isinstance(result, dict) and result.get("requires_2fa"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA verification required"
        )

    # Set refresh token as httpOnly cookie
    set_refresh_token_cookie(response, result.refresh_token)

    return {
        "access_token": result.access_token,
        "token_type": result.token_type,
        "expires_in": result.expires_in
    }

@router.post("/refresh")
async def refresh_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
    device_fingerprint: str = Depends(get_device_fingerprint),
    ip: str = Depends(get_client_ip),
    _: None = Depends(validate_csrf_token)  # CSRF protection
):
    """
    Làm mới access token bằng refresh token từ cookie

    Returns: Access token mới (refresh token mới set as httpOnly cookie)
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )

    # Query all active (non-revoked, non-expired) tokens
    stmt = select(RefreshToken).where(
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    )
    result = await db.execute(stmt)
    active_tokens = result.scalars().all()

    # Find matching token by verifying hash
    token_record = None
    for token in active_tokens:
        if verify_refresh_token(token.token_hash, refresh_token):
            token_record = token
            break

    if not token_record:
        # Clear invalid cookie
        clear_refresh_token_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Revoke token cũ
    token_record.is_revoked = True
    await db.commit()

    # Tạo token mới
    new_tokens = await AuthService._generate_tokens(
        db,
        token_record.user_id,
        device_fingerprint,
        ip
    )

    # Set new refresh token as httpOnly cookie
    set_refresh_token_cookie(response, new_tokens.refresh_token)

    return {
        "access_token": new_tokens.access_token,
        "token_type": new_tokens.token_type,
        "expires_in": new_tokens.expires_in
    }

@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(validate_csrf_token)  # CSRF protection
):
    """
    Đăng xuất - revoke refresh token và xóa cookie

    Returns: Success message
    """
    if refresh_token:
        # Query all non-revoked tokens
        stmt = select(RefreshToken).where(RefreshToken.is_revoked == False)
        result = await db.execute(stmt)
        active_tokens = result.scalars().all()

        # Find matching token by verifying hash
        token_record = None
        for token in active_tokens:
            if verify_refresh_token(token.token_hash, refresh_token):
                token_record = token
                break

        # Revoke token if found
        if token_record:
            token_record.is_revoked = True
            await db.commit()

    # Clear refresh token cookie
    clear_refresh_token_cookie(response)

    return MessageResponse(message="Logged out successfully")
