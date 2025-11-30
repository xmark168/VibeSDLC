"""Profile API routes for user profile management."""

import logging
import os
import uuid
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from PIL import Image
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings

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
