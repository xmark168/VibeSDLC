"""Two-Factor Authentication schemas."""

from uuid import UUID
from pydantic import BaseModel, Field


class TwoFactorSetupResponse(BaseModel):
    """Response for 2FA setup - contains secret and QR code."""
    secret: str
    qr_code_uri: str
    message: str = "Scan the QR code with your authenticator app"


class TwoFactorVerifySetupRequest(BaseModel):
    """Request to verify and enable 2FA."""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class TwoFactorVerifySetupResponse(BaseModel):
    """Response after successfully enabling 2FA."""
    message: str = "Two-factor authentication enabled successfully"
    backup_codes: list[str]


class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA."""
    password: str = Field(..., min_length=1, description="Current password for verification")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code or backup code")


class TwoFactorDisableResponse(BaseModel):
    """Response after disabling 2FA."""
    message: str = "Two-factor authentication disabled successfully"


class TwoFactorVerifyRequest(BaseModel):
    """Request to verify 2FA during login."""
    temp_token: str = Field(..., description="Temporary token from login")
    code: str = Field(..., min_length=6, max_length=8, description="6-digit TOTP code or backup code")


class TwoFactorVerifyResponse(BaseModel):
    """Response after successful 2FA verification during login."""
    user_id: UUID
    access_token: str
    refresh_token: str


class TwoFactorStatusResponse(BaseModel):
    """Response for 2FA status check."""
    enabled: bool
    has_backup_codes: bool


class TwoFactorBackupCodesResponse(BaseModel):
    """Response with new backup codes."""
    backup_codes: list[str]
    message: str = "New backup codes generated. Store them safely."


class LoginRequires2FAResponse(BaseModel):
    """Response when login requires 2FA verification."""
    requires_2fa: bool = True
    temp_token: str
    message: str = "Two-factor authentication required"
