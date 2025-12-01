"""Profile API routes for user profile management."""

import logging
import os
import re
import uuid
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from PIL import Image
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["profile"])

# Avatar settings
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_SIZE = (256, 256)  # Final avatar dimensions

# Default avatar for email users
DEFAULT_AVATAR_URL = "https://github.com/shadcn.png"

# Uploads directory
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads")
AVATARS_DIR = os.path.join(UPLOADS_DIR, "avatars")


class ProfileUpdate(BaseModel):
    """Request to update profile"""
    full_name: str | None = None


class ChangePasswordRequest(BaseModel):
    """Request to change password (for users with existing password)"""
    current_password: str
    new_password: str
    confirm_password: str


class SetPasswordRequest(BaseModel):
    """Request to set password (for OAuth users without password)"""
    new_password: str
    confirm_password: str


class PasswordStatusResponse(BaseModel):
    """Password status response"""
    has_password: bool
    login_provider: str | None


class PasswordChangeResponse(BaseModel):
    """Password change response"""
    message: str


class ProfileResponse(BaseModel):
    """Profile response"""
    id: str
    email: str
    full_name: str | None
    avatar_url: str | None
    login_provider: str | None

    class Config:
        from_attributes = True


class AvatarUploadResponse(BaseModel):
    """Avatar upload response"""
    avatar_url: str
    message: str


def get_avatar_url(user) -> str:
    """Get avatar URL for user, with fallback to default"""
    if user.avatar_url:
        return user.avatar_url
    return DEFAULT_AVATAR_URL


@router.get("/me", response_model=ProfileResponse)
def get_profile(
    current_user: CurrentUser,
) -> ProfileResponse:
    """Get current user's profile"""
    return ProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=get_avatar_url(current_user),
        login_provider=current_user.login_provider,
    )


@router.patch("/me", response_model=ProfileResponse)
def update_profile(
    profile_data: ProfileUpdate,
    current_user: CurrentUser,
    session: SessionDep,
) -> ProfileResponse:
    """Update current user's profile"""
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name.strip()

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return ProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=get_avatar_url(current_user),
        login_provider=current_user.login_provider,
    )


@router.post("/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    current_user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(...),
) -> AvatarUploadResponse:
    """
    Upload and crop avatar image.
    Accepts PNG, JPG, JPEG, GIF, WEBP. Max 5MB.
    Image will be resized to 256x256.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    try:
        # Open and process image
        image = Image.open(BytesIO(content))

        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Resize image to square (crop center if needed)
        width, height = image.size
        min_dim = min(width, height)

        # Crop to center square
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim
        image = image.crop((left, top, right, bottom))

        # Resize to final dimensions
        image = image.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)

        # Generate unique filename
        filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(AVATARS_DIR, filename)

        # Delete old avatar if exists
        if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/avatars/"):
            old_filename = current_user.avatar_url.split("/")[-1]
            old_filepath = os.path.join(AVATARS_DIR, old_filename)
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                except Exception as e:
                    logger.warning(f"Failed to delete old avatar: {e}")

        # Save new avatar
        image.save(filepath, "JPEG", quality=90)

        # Update user's avatar_url
        avatar_url = f"/uploads/avatars/{filename}"
        current_user.avatar_url = avatar_url
        session.add(current_user)
        session.commit()

        logger.info(f"Avatar uploaded for user {current_user.id}: {avatar_url}")

        return AvatarUploadResponse(
            avatar_url=avatar_url,
            message="Avatar uploaded successfully"
        )

    except Exception as e:
        logger.error(f"Error processing avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process image"
        )


@router.delete("/avatar")
def delete_avatar(
    current_user: CurrentUser,
    session: SessionDep,
):
    """Delete current user's avatar and reset to default"""
    if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/avatars/"):
        filename = current_user.avatar_url.split("/")[-1]
        filepath = os.path.join(AVATARS_DIR, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Failed to delete avatar file: {e}")

    current_user.avatar_url = None
    session.add(current_user)
    session.commit()

    return {"message": "Avatar deleted", "avatar_url": DEFAULT_AVATAR_URL}


def validate_password(password: str) -> bool:
    """Validate password: min 8 chars, at least 1 letter and 1 number"""
    if len(password) < 8:
        return False
    has_letter = bool(re.search(r"[a-zA-Z]", password))
    has_number = bool(re.search(r"\d", password))
    return has_letter and has_number


@router.get("/password-status", response_model=PasswordStatusResponse)
def get_password_status(
    current_user: CurrentUser,
) -> PasswordStatusResponse:
    """Check if user has password set"""
    return PasswordStatusResponse(
        has_password=current_user.hashed_password is not None,
        login_provider=current_user.login_provider,
    )


@router.post("/change-password", response_model=PasswordChangeResponse)
def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> PasswordChangeResponse:
    """
    Change password for users who already have a password.
    Requires current password verification.
    """
    # Check if user has a password
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn chưa có mật khẩu. Vui lòng sử dụng chức năng tạo mật khẩu.",
        )

    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mật khẩu hiện tại không đúng",
        )

    # Validate new password
    if not validate_password(password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mật khẩu mới phải có ít nhất 8 ký tự, chứa ít nhất 1 chữ cái và 1 chữ số",
        )

    # Check password confirmation
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu xác nhận không khớp",
        )

    # Check new password is different from current
    if verify_password(password_data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải khác mật khẩu hiện tại",
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    session.add(current_user)
    session.commit()

    logger.info(f"Password changed for user {current_user.id}")

    return PasswordChangeResponse(message="Đổi mật khẩu thành công")


@router.post("/set-password", response_model=PasswordChangeResponse)
def set_password(
    password_data: SetPasswordRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> PasswordChangeResponse:
    """
    Set password for OAuth users who don't have a password yet.
    This allows them to login with email + password.
    """
    # Check if user already has a password
    if current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã có mật khẩu. Vui lòng sử dụng chức năng đổi mật khẩu.",
        )

    # Validate new password
    if not validate_password(password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mật khẩu phải có ít nhất 8 ký tự, chứa ít nhất 1 chữ cái và 1 chữ số",
        )

    # Check password confirmation
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu xác nhận không khớp",
        )

    # Set password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    session.add(current_user)
    session.commit()

    logger.info(f"Password set for OAuth user {current_user.id}")

    return PasswordChangeResponse(message="Tạo mật khẩu thành công. Bạn có thể đăng nhập bằng email và mật khẩu.")
