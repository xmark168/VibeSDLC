"""Profile API routes for user profile management."""

import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from PIL import Image

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.services.singletons import get_minio_service
from app.schemas.profile import (
    ProfileUpdate,
    ChangePasswordRequest,
    SetPasswordRequest,
    PasswordStatusResponse,
    PasswordChangeResponse,
    ProfileResponse,
    AvatarUploadResponse,
)
from app.utils.generators import get_avatar_url, DEFAULT_AVATAR_URL
from app.utils.validators import validate_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["profile"])

# Avatar settings
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_SIZE = (256, 256)  # Final avatar dimensions


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

        # Save image to BytesIO for MinIO upload
        output = BytesIO()
        image.save(output, "JPEG", quality=90, optimize=True)
        output.seek(0)
        
        # Upload to MinIO
        minio = get_minio_service()
        object_name = f"avatars/{filename}"
        avatar_url = minio.upload_file(
            file_data=output.getvalue(),
            object_name=object_name,
            content_type="image/jpeg"
        )
        
        # Delete old avatar from MinIO if exists
        if current_user.avatar_url and "avatars/" in current_user.avatar_url:
            old_object = current_user.avatar_url.split("/images/")[-1]
            try:
                minio.delete_file(old_object)
                logger.info(f"Deleted old avatar from MinIO: {old_object}")
            except Exception as e:
                logger.warning(f"Failed to delete old avatar from MinIO: {e}")

        # Update user's avatar_url
        current_user.avatar_url = avatar_url
        session.add(current_user)
        session.commit()

        logger.info(f"Avatar uploaded for user {current_user.id} to MinIO: {avatar_url}")

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
    # Delete from MinIO if exists
    if current_user.avatar_url and "avatars/" in current_user.avatar_url:
        minio = get_minio_service()
        object_name = current_user.avatar_url.split("/images/")[-1]
        try:
            minio.delete_file(object_name)
            logger.info(f"Deleted avatar from MinIO: {object_name}")
        except Exception as e:
            logger.warning(f"Failed to delete avatar from MinIO: {e}")

    current_user.avatar_url = None
    session.add(current_user)
    session.commit()

    return {"message": "Avatar deleted", "avatar_url": DEFAULT_AVATAR_URL}


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
            detail="You don't have a password yet. Please use the create password feature.",
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

    return PasswordChangeResponse(success=True, message="Đổi mật khẩu thành công")


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
            detail="You already have a password. Please use the change password feature.",
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

    return PasswordChangeResponse(
        success=True,
        message="Tạo mật khẩu thành công. Bạn có thể đăng nhập bằng email và mật khẩu."
    )
