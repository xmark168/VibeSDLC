from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD
from app.schemas import TokenResponse, UserRegister, UserLogin
from app.models import User, RefreshToken
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from fastapi import Depends, HTTPException, status
from app.core.config import settings
from app.database import get_db
user_crud = FastCRUD(User)
refresh_token_crud = FastCRUD(RefreshToken)

class AuthService:
    @staticmethod
    async def register(data: UserRegister, device_fingerprint: str, ip: str, db: AsyncSession):
        # 1. Kiểm tra user tồn tại
        existing = await user_crud.get(db, email=data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_username = await user_crud.get(db, username=data.username)
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # 2. Hash password & tạo user
        hashed_pwd = hash_password(data.password)
        new_user = await user_crud.create(
            db,
            {
                "username": data.username,
                "email": data.email,
                "password_hash": hashed_pwd,
                "fullname": data.fullname,
            },
            commit=True
        )

        # 3. Tạo refresh token
        refresh_token, token_hash = create_refresh_token()
        await refresh_token_crud.create(
            db,
            {
                "user_id": new_user.id,
                "token_hash": token_hash,
                "device_fingerprint": device_fingerprint,
                "ip_address": ip,
                "expires_at": datetime.now(timezone.utc()) + timedelta(days=30),
            },
            commit=True
        )

        # 4. Tạo access token
        access_token = create_access_token({"sub": str(new_user.id)})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        ), new_user
    
    @staticmethod
    async def login(data: UserLogin, device_fingerprint: str, ip: str, db: AsyncSession):
         # 1. Tìm user
        user = await user_crud.get(db, email=data.username_or_email)
        if not user:
            user = await user_crud.get(db, username=data.username_or_email)
        
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không hợp lệ")
        
        # 2. Check locked account
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(status_code=403, detail="Tài khoản của bạn đã bị tạm thời khóa. Vui lòng liên hệ quản trị viên để biết thêm thông tin")
        
        # 3. Verify password
        if not verify_password(data.password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            await db.commit()
            raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không hợp lệ")
        
        # Reset attempts on success
        user.failed_login_attempts = 0
        await db.commit()

        # 4. Check 2FA
        if user.two_factor_enabled:
            return {"requires_2fa": True, "user_id": user.id}
        
        # 5. Generate tokens
        return await AuthService._generate_tokens(db, user.id, device_fingerprint, ip)
    
    @staticmethod
    async def _generate_tokens(db: AsyncSession, user_id: int, device_fingerprint: str, ip: str):
        access_token = create_access_token({"sub": str(user_id)})
        refresh_token, token_hash = create_refresh_token()
        
        await refresh_token_crud.create(
            db,
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "device_fingerprint": device_fingerprint,
                "ip_address": ip,
                "expires_at": datetime.now(timezone.utc()) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            },
            commit=True
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )