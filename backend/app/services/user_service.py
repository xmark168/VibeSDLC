from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD
from fastapi import HTTPException, status
from app.models import User
from app.schemas import UserUpdate, ChangePassword
from app.core.security import hash_password, verify_password

user_crud = FastCRUD(User)

class UserService:
    @staticmethod
    async def get_user_by_id(user_id: int, db: AsyncSession) -> User:
        """Lấy user theo ID"""
        user = await user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    @staticmethod
    async def update_user_profile(user_id: int, data: UserUpdate, db: AsyncSession) -> User:
        """Cập nhật thông tin user"""
        user = await user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Chuẩn bị data để update (chỉ update các field không None)
        update_data = data.model_dump(exclude_unset=True)

        if update_data:
            updated_user = await user_crud.update(
                db,
                object=user,
                **update_data
            )
            await db.commit()
            await db.refresh(updated_user)
            return updated_user

        return user

    @staticmethod
    async def change_password(user_id: int, data: ChangePassword, db: AsyncSession) -> dict:
        """Đổi password"""
        user = await user_crud.get(db, id=user_id)
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
        new_hash = hash_password(data.new_password)
        await user_crud.update(
            db,
            object=user,
            password_hash=new_hash
        )
        await db.commit()

        return {"message": "Password changed successfully"}
