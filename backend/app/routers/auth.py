from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address
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
from app.core.security import verify_refresh_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)

def get_device_fingerprint(x_device_fingerprint: str = Header(None)) -> str:
    """Extract device fingerprint from header"""
    return x_device_fingerprint or "unknown"

def get_client_ip(request: Request) -> str:
    """Extract client IP address"""
    return request.client.host if request.client else "unknown"

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def register(
    request: Request,
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
    device_fingerprint: str = Depends(get_device_fingerprint),
    ip: str = Depends(get_client_ip)
):
    """
    Đăng ký tài khoản mới

    **Rate Limit:** 3 requests per hour

    Returns: Token response và thông tin user
    """
    token_response, user = await AuthService.register(data, device_fingerprint, ip, db)

    return {
        "message": "User registered successfully",
        "tokens": token_response,
        "user": UserResponse.model_validate(user)
    }

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
    device_fingerprint: str = Depends(get_device_fingerprint),
    ip: str = Depends(get_client_ip)
):
    """
    Đăng nhập

    **Rate Limit:** 5 requests per minute

    - **username_or_email**: Username hoặc email
    - **password**: Mật khẩu

    Returns: Access token và refresh token
    """
    result = await AuthService.login(data, device_fingerprint, ip, db)

    # Nếu cần 2FA, trả về message khác
    if isinstance(result, dict) and result.get("requires_2fa"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA verification required"
        )

    return result

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    device_fingerprint: str = Depends(get_device_fingerprint),
    ip: str = Depends(get_client_ip)
):
    """
    Làm mới access token bằng refresh token

    **Rate Limit:** 10 requests per minute

    - **refresh_token**: Refresh token nhận được từ login/register

    Returns: Access token và refresh token mới
    """
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
        if verify_refresh_token(token.token_hash, data.refresh_token):
            token_record = token
            break

    if not token_record:
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

    return new_tokens

@router.post("/logout", response_model=MessageResponse)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Đăng xuất - revoke refresh token

    **Rate Limit:** 20 requests per minute

    - **refresh_token**: Refresh token cần revoke

    Returns: Success message
    """
    # Query all non-revoked tokens
    stmt = select(RefreshToken).where(RefreshToken.is_revoked == False)
    result = await db.execute(stmt)
    active_tokens = result.scalars().all()

    # Find matching token by verifying hash
    token_record = None
    for token in active_tokens:
        if verify_refresh_token(token.token_hash, data.refresh_token):
            token_record = token
            break

    # Revoke token if found
    if token_record:
        token_record.is_revoked = True
        await db.commit()

    return MessageResponse(message="Logged out successfully")
