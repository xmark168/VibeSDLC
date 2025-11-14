from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models import User
from app.schemas import UserUpdate, ChangePassword, UserResponse
from app.core.security import hash_password, verify_password

class UserService:
    @staticmethod
    async def get_user_by_id(user_id: int, db: AsyncSession) -> User:
        """Lấy user theo ID"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    @staticmethod
    async def update_user_profile(user_id: int, data: UserUpdate, db: AsyncSession) -> User:
        """Cập nhật thông tin user"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Chuẩn bị data để update (chỉ update các field không None)
        update_data = data.model_dump(exclude_unset=True)

        if update_data:
            for key, value in update_data.items():
                setattr(user, key, value)
            await db.commit()
            await db.refresh(user)

        return user

    @staticmethod
    async def change_password(user_id: int, data: ChangePassword, db: AsyncSession) -> dict:
        """Đổi password"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify old password
        if not verify_password(data.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Old password is incorrect"
            )

        # Update with new password
        user.password_hash = hash_password(data.new_password)
        await db.commit()

        return {"message": "Password changed successfully"}
