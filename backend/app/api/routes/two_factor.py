"""Two-Factor Authentication API routes."""

import logging
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
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
    TwoFactorStatusResponse,
    TwoFactorBackupCodesResponse,
)
from app.services import TwoFactorService

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


@router.post("/disable", response_model=TwoFactorDisableResponse)
@limiter.limit("3/minute")
def disable_2fa(
    request: Request,
    disable_data: TwoFactorDisableRequest,
    current_user: CurrentUser,
    session: SessionDep
) -> TwoFactorDisableResponse:
    """
    Disable 2FA for the authenticated user.
    Requires password and valid TOTP/backup code.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify password
    if not verify_password(disable_data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    two_factor_service = TwoFactorService(session)
    
    try:
        two_factor_service.disable_2fa(current_user, disable_data.code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return TwoFactorDisableResponse(message="Two-factor authentication disabled successfully")


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
