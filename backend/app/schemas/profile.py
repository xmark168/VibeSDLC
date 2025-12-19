"""Profile-related schemas."""

from pydantic import BaseModel, Field, validator
from uuid import UUID
from datetime import datetime


class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: str | None = None
    bio: str | None = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "bio": "Software Engineer"
            }
        }


class ChangePasswordRequest(BaseModel):
    """Request to change password (requires current password)."""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class SetPasswordRequest(BaseModel):
    """Request to set initial password (no current password required)."""
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordStatusResponse(BaseModel):
    """Response indicating if user has password set."""
    has_password: bool


class PasswordChangeResponse(BaseModel):
    """Response after password change attempt."""
    message: str
    success: bool


class ProfileResponse(BaseModel):
    """Complete user profile response."""
    id: UUID
    email: str
    full_name: str | None
    bio: str | None
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AvatarUploadResponse(BaseModel):
    """Response after avatar upload."""
    avatar_url: str
    message: str
