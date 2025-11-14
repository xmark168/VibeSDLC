from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import UserResponse, UserUpdate, ChangePassword, MessageResponse
from app.services.user_service import UserService
from app.dependencies import get_current_active_user
from app.models import User

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Lấy thông tin profile của user hiện tại

    Requires: Valid access token

    Returns: User information
    """
    return UserResponse.model_validate(current_user)

@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật thông tin profile

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
async def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Đổi mật khẩu

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
