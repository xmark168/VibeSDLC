from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app.schemas import UserResponse, UserUpdate, ChangePassword, MessageResponse
from app.services.user_service import UserService
from app.dependencies import get_current_active_user
from app.models import User

router = APIRouter(prefix="/users", tags=["Users"])
limiter = Limiter(key_func=get_remote_address)

@router.get("/me", response_model=UserResponse)
@limiter.limit("30/minute")
async def get_my_profile(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Lấy thông tin profile của user hiện tại

    **Rate Limit:** 30 requests per minute

    Requires: Valid access token

    Returns: User information
    """
    return UserResponse.model_validate(current_user)

@router.put("/me", response_model=UserResponse)
@limiter.limit("10/minute")
async def update_my_profile(
    request: Request,
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật thông tin profile

    **Rate Limit:** 10 requests per minute

    Requires: Valid access token

    - **fullname**: Tên đầy đủ (optional)
    - **address**: Địa chỉ (optional)

    Returns: Updated user information
    """
    updated_user = await UserService.update_user_profile(
        current_user.id,
        data,
        db
    )
    return UserResponse.model_validate(updated_user)

@router.post("/change-password", response_model=MessageResponse)
@limiter.limit("5/hour")
async def change_password(
    request: Request,
    data: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Đổi mật khẩu

    **Rate Limit:** 5 requests per hour (security sensitive)

    Requires: Valid access token

    - **old_password**: Mật khẩu hiện tại
    - **new_password**: Mật khẩu mới (tối thiểu 8 ký tự)

    Returns: Success message
    """
    result = await UserService.change_password(
        current_user.id,
        data,
        db
    )
    return MessageResponse(**result)
