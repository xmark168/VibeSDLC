from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
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
from fastcrud import FastCRUD

router = APIRouter(prefix="/auth", tags=["Authentication"])
refresh_token_crud = FastCRUD(RefreshToken)

def get_device_fingerprint(x_device_fingerprint: str = Header(None)) -> str:
    """Extract device fingerprint from header"""
    return x_device_fingerprint or "unknown"

def get_client_ip(request: Request) -> str:
    """Extract client IP address"""
    return request.client.host if request.client else "unknown"

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
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

    return {
        "message": "User registered successfully",
        "tokens": token_response,
        "user": UserResponse.model_validate(user)
    }

@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
    device_fingerprint: str = Depends(get_device_fingerprint),
    ip: str = Depends(get_client_ip)
):
    """
    Đăng nhập

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
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    device_fingerprint: str = Depends(get_device_fingerprint),
    ip: str = Depends(get_client_ip)
):
    """
    Làm mới access token bằng refresh token

    - **refresh_token**: Refresh token nhận được từ login/register

    Returns: Access token và refresh token mới
    """
    # Tìm refresh token trong database
    token_record = await refresh_token_crud.get(db, token_hash=data.refresh_token)

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Kiểm tra token có bị revoke không
    if token_record.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    # Kiểm tra token có hết hạn không
    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )

    # Verify token
    if not verify_refresh_token(token_record.token_hash, data.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Revoke token cũ
    await refresh_token_crud.update(
        db,
        object=token_record,
        is_revoked=True
    )
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
async def logout(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Đăng xuất - revoke refresh token

    - **refresh_token**: Refresh token cần revoke

    Returns: Success message
    """
    # Tìm và revoke token
    token_record = await refresh_token_crud.get(db, token_hash=data.refresh_token)

    if token_record and not token_record.is_revoked:
        await refresh_token_crud.update(
            db,
            object=token_record,
            is_revoked=True
        )
        await db.commit()

    return MessageResponse(message="Logged out successfully")
