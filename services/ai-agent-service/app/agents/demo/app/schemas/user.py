"""
User Pydantic schemas for request/response validation.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    def validate_passwords_match(self) -> "UserCreate":
        """Validate that password and confirm_password match."""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserUpdate(BaseModel):
    """Schema for user updates."""

    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserUpdatePassword(BaseModel):
    """Schema for password updates."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

    def validate_passwords_match(self) -> "UserUpdatePassword":
        """Validate that new passwords match."""
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")
        return self


class UserResponse(UserBase):
    """Schema for user responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_verified: bool
    is_superuser: bool


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class UserToken(BaseModel):
    """Schema for authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserTokenRefresh(BaseModel):
    """Schema for token refresh."""

    refresh_token: str


class UserPasswordReset(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class UserPasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

    def validate_passwords_match(self) -> "UserPasswordResetConfirm":
        """Validate that passwords match."""
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match")
        return self


class UserVerifyEmail(BaseModel):
    """Schema for email verification."""

    token: str
