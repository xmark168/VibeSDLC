"""Two-Factor Authentication API routes."""

import logging
import random
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.security import verify_password
from app.models import User
from app.schemas import (
    TwoFactorSetupResponse,
    TwoFactorVerifySetupRequest,
    TwoFactorVerifySetupResponse,
    TwoFactorDisableRequest,
    TwoFactorDisableResponse,
    TwoFactorRequestDisableRequest,
    TwoFactorRequestDisableResponse,
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
    TwoFactorStatusResponse,
    TwoFactorBackupCodesResponse,
)
from app.services import TwoFactorService
from app.utils import send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/2fa", tags=["two-factor-authentication"])

limiter = Limiter(key_func=get_remote_address)
redis_client = get_redis_client()

TEMP_TOKEN_PREFIX = "2fa_temp:"
TEMP_TOKEN_TTL = 300  # 5 minutes


@router.get("/status", response_model=TwoFactorStatusResponse)
def get_2fa_status(current_user: CurrentUser, session: SessionDep) -> TwoFactorStatusResponse:
    """Get current 2FA status for authenticated user."""
    two_factor_service = TwoFactorService(session)
    status_data = two_factor_service.get_2fa_status(current_user)
    return TwoFactorStatusResponse(**status_data)


@router.post("/setup", response_model=TwoFactorSetupResponse)
def setup_2fa(current_user: CurrentUser, session: SessionDep) -> TwoFactorSetupResponse:
    """
    Initialize 2FA setup - generates secret and QR code.
    User must call /verify-setup with a valid code to complete setup.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )
    
    two_factor_service = TwoFactorService(session)
    secret, qr_code = two_factor_service.setup_2fa(current_user)
    
    return TwoFactorSetupResponse(
        secret=secret,
        qr_code_uri=qr_code,
        message="Scan the QR code with your authenticator app, then verify with a code"
    )


@router.post("/verify-setup", response_model=TwoFactorVerifySetupResponse)
@limiter.limit("5/minute")
def verify_2fa_setup(
    request: Request,
    verify_data: TwoFactorVerifySetupRequest,
    current_user: CurrentUser,
    session: SessionDep
) -> TwoFactorVerifySetupResponse:
    """
    Verify TOTP code and complete 2FA setup.
    Returns backup codes that should be stored safely.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )
    
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated. Call /setup first"
        )
    
    two_factor_service = TwoFactorService(session)
    
    try:
        backup_codes = two_factor_service.verify_and_enable_2fa(current_user, verify_data.code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return TwoFactorVerifySetupResponse(
        message="Two-factor authentication enabled successfully",
        backup_codes=backup_codes
    )


def generate_verification_code() -> str:
    """Generate 6-digit verification code"""
    return str(random.randint(100000, 999999))


def mask_email(email: str) -> str:
    """Mask email for display (e.g., t***@gmail.com)"""
    if "@" not in email:
        return email
    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


def generate_disable_2fa_email(email_to: str, code: str) -> tuple[str, str]:
    """Generate email content for 2FA disable verification."""
    from app.core.config import settings
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Disable 2FA Verification Code"
    html_content = f"""
    <html>
    <body>
        <h2>Disable Two-Factor Authentication (2FA)</h2>
        <p>Hello,</p>
        <p>You have requested to disable two-factor authentication for your account.</p>
        <p>Your verification code is: <strong style="font-size: 24px; color: #dc3545;">{code}</strong></p>
        <p>This code is valid for 3 minutes.</p>
        <p><strong>Warning:</strong> If you did not request to disable 2FA, please ignore this email and check your account security.</p>
        <br>
        <p>Best regards,<br>{project_name} Team</p>
    </body>
    </html>
    """
    return subject, html_content


DISABLE_2FA_CODE_PREFIX = "disable_2fa_code:"
DISABLE_2FA_CODE_TTL = 180  # 3 minutes


@router.post("/request-disable", response_model=TwoFactorRequestDisableResponse)
@limiter.limit("3/minute")
def request_disable_2fa(
    request: Request,
    request_data: TwoFactorRequestDisableRequest,
    current_user: CurrentUser,
    session: SessionDep
) -> TwoFactorRequestDisableResponse:
    """
    Request to disable 2FA - sends verification code to email.
    User must call /disable with the code to complete.
    Password is required for credential users, optional for OAuth users.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Check if user has password - if yes, require password verification
    has_password = current_user.hashed_password is not None
    
    # Verify password for users who have password set
    if has_password:
        if not request_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required"
            )
        if not verify_password(request_data.password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )
    
    # Generate verification code
    code = generate_verification_code()
    
    # Store code in Redis
    code_key = f"{DISABLE_2FA_CODE_PREFIX}{current_user.id}"
    if not redis_client.set(code_key, code, ttl=DISABLE_2FA_CODE_TTL):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống, vui lòng thử lại"
        )
    
    # Send verification email
    try:
        subject, html_content = generate_disable_2fa_email(current_user.email, code)
        send_email(
            email_to=current_user.email,
            subject=subject,
            html_content=html_content,
        )
    except Exception as e:
        logger.error(f"Failed to send disable 2FA email: {e}")
        redis_client.delete(code_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể gửi email xác thực"
        )
    
    return TwoFactorRequestDisableResponse(
        message="Verification code has been sent to your email",
        masked_email=mask_email(current_user.email),
        expires_in=DISABLE_2FA_CODE_TTL
    )


@router.post("/disable", response_model=TwoFactorDisableResponse)
@limiter.limit("5/minute")
def disable_2fa(
    request: Request,
    disable_data: TwoFactorDisableRequest,
    current_user: CurrentUser,
    session: SessionDep
) -> TwoFactorDisableResponse:
    """
    Disable 2FA for the authenticated user.
    Requires email verification code. Password required for non-OAuth users.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Check if user is OAuth user (no password required)
    is_oauth_user = current_user.login_provider is not None
    
    # Verify password for non-OAuth users
    if not is_oauth_user:
        if not disable_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required"
            )
        if not verify_password(disable_data.password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )
    
    code = disable_data.code.replace("-", "").replace(" ", "")
    
    # First, check if the code matches email verification code
    code_key = f"{DISABLE_2FA_CODE_PREFIX}{current_user.id}"
    stored_code = redis_client.get(code_key)
    
    if stored_code and str(stored_code).strip() == code.strip():
        # Email verification code is valid - disable 2FA directly
        current_user.two_factor_enabled = False
        current_user.totp_secret = None
        current_user.backup_codes = None
        session.add(current_user)
        session.commit()
        
        # Clean up Redis
        redis_client.delete(code_key)
        
        return TwoFactorDisableResponse(message="Two-factor authentication has been disabled successfully")
    
    # If not email code, try TOTP/backup code
    two_factor_service = TwoFactorService(session)
    
    try:
        two_factor_service.disable_2fa(current_user, disable_data.code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    return TwoFactorDisableResponse(message="Two-factor authentication has been disabled successfully")


@router.post("/verify", response_model=TwoFactorVerifyResponse)
@limiter.limit("5/minute")
def verify_2fa_login(
    request: Request,
    response: Response,
    verify_data: TwoFactorVerifyRequest,
    session: SessionDep
) -> TwoFactorVerifyResponse:
    """
    Verify 2FA code during login flow.
    Requires temp_token from login response and valid TOTP/backup code.
    """
    # Get user_id from temp token in Redis
    token_key = f"{TEMP_TOKEN_PREFIX}{verify_data.temp_token}"
    user_id = redis_client.get(token_key)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification session"
        )
    
    # Get user from database
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify 2FA code
    two_factor_service = TwoFactorService(session)
    if not two_factor_service.verify_2fa_login(user, verify_data.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code"
        )
    
    # Delete temp token
    redis_client.delete(token_key)
    
    # Create full access tokens
    access_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )
    
    refresh_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )
    
    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    
    return TwoFactorVerifyResponse(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/backup-codes", response_model=TwoFactorBackupCodesResponse)
@limiter.limit("3/hour")
def regenerate_backup_codes(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep
) -> TwoFactorBackupCodesResponse:
    """
    Regenerate backup codes.
    Old backup codes will be invalidated.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    two_factor_service = TwoFactorService(session)
    
    try:
        backup_codes = two_factor_service.regenerate_backup_codes(current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return TwoFactorBackupCodesResponse(
        backup_codes=backup_codes,
        message="New backup codes generated. Store them safely. Old codes are now invalid."
    )
