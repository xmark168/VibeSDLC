from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    fullname: str = None

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TwoFactorVerify(BaseModel):
    user_id: int
    code: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    fullname: Optional[str] = None
    is_active: bool
    balance: float
    created_at: datetime
    updated_at: datetime
    locked_until: Optional[datetime] = None
    failed_login_attempts: int = 0
    two_factor_enabled: bool = False
    address: Optional[str] = None  # Changed from dict to str to match database

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    fullname: Optional[str] = None
    address: Optional[str] = None

class ChangePassword(BaseModel):
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class MessageResponse(BaseModel):
    message: str

# ==================== Create Schemas ====================

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    username: str
    email: str
    password_hash: str
    fullname: Optional[str] = None

class RefreshTokenCreate(BaseModel):
    """Schema for creating a refresh token"""
    user_id: int
    token_hash: str
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    expires_at: datetime