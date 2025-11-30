"""Two-Factor Authentication Service - Encapsulates all 2FA business logic."""

import secrets
import hashlib
import base64
from typing import Tuple
from io import BytesIO

import pyotp
import qrcode
from sqlmodel import Session

from app.models import User
from app.core.config import settings


class TwoFactorService:
    """Service for two-factor authentication management."""
    
    BACKUP_CODE_COUNT = 10
    BACKUP_CODE_LENGTH = 8
    
    def __init__(self, session: Session):
        self.session = session
    
    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    def get_totp_uri(self, user: User, secret: str) -> str:
        """Generate TOTP URI for QR code scanning."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user.email,
            issuer_name=getattr(settings, 'PROJECT_NAME', 'VibeSDLC')
        )
    
    def generate_qr_code_base64(self, uri: str) -> str:
        """Generate QR code as base64 encoded PNG."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    
    def verify_totp_code(self, secret: str, code: str) -> bool:
        """Verify a TOTP code against the secret."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    
    def generate_backup_codes(self) -> Tuple[list[str], list[str]]:
        """
        Generate backup codes.
        Returns tuple of (plain_codes, hashed_codes).
        Plain codes are shown to user once, hashed codes are stored.
        """
        plain_codes = []
        hashed_codes = []
        
        for _ in range(self.BACKUP_CODE_COUNT):
            code = secrets.token_hex(self.BACKUP_CODE_LENGTH // 2).upper()
            formatted_code = f"{code[:4]}-{code[4:]}"
            plain_codes.append(formatted_code)
            hashed_codes.append(self._hash_backup_code(formatted_code))
        
        return plain_codes, hashed_codes
    
    def _hash_backup_code(self, code: str) -> str:
        """Hash a backup code for secure storage."""
        normalized = code.replace("-", "").upper()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def verify_backup_code(self, user: User, code: str) -> bool:
        """
        Verify and consume a backup code.
        Returns True if valid, False otherwise.
        """
        if not user.backup_codes:
            return False
        
        code_hash = self._hash_backup_code(code)
        
        if code_hash in user.backup_codes:
            user.backup_codes = [c for c in user.backup_codes if c != code_hash]
            self.session.add(user)
            self.session.commit()
            return True
        
        return False
    
    def setup_2fa(self, user: User) -> Tuple[str, str]:
        """
        Initialize 2FA setup for a user.
        Returns tuple of (secret, qr_code_base64).
        Does NOT enable 2FA yet - user must verify first.
        """
        secret = self.generate_totp_secret()
        uri = self.get_totp_uri(user, secret)
        qr_code = self.generate_qr_code_base64(uri)
        
        user.totp_secret = secret
        self.session.add(user)
        self.session.commit()
        
        return secret, qr_code
    
    def verify_and_enable_2fa(self, user: User, code: str) -> list[str]:
        """
        Verify TOTP code and enable 2FA.
        Returns backup codes on success.
        Raises ValueError if verification fails.
        """
        if not user.totp_secret:
            raise ValueError("2FA setup not initiated")
        
        if not self.verify_totp_code(user.totp_secret, code):
            raise ValueError("Invalid verification code")
        
        plain_codes, hashed_codes = self.generate_backup_codes()
        
        user.two_factor_enabled = True
        user.backup_codes = hashed_codes
        self.session.add(user)
        self.session.commit()
        
        return plain_codes
    
    def disable_2fa(self, user: User, code: str) -> bool:
        """
        Disable 2FA for a user.
        Requires valid TOTP code or backup code.
        Returns True on success.
        """
        if not user.two_factor_enabled:
            raise ValueError("2FA is not enabled")
        
        is_valid = self.verify_totp_code(user.totp_secret, code) or self.verify_backup_code(user, code)
        
        if not is_valid:
            raise ValueError("Invalid verification code")
        
        user.two_factor_enabled = False
        user.totp_secret = None
        user.backup_codes = None
        self.session.add(user)
        self.session.commit()
        
        return True
    
    def verify_2fa_login(self, user: User, code: str) -> bool:
        """
        Verify 2FA code during login.
        Accepts TOTP code or backup code.
        """
        if not user.two_factor_enabled or not user.totp_secret:
            return False
        
        if self.verify_totp_code(user.totp_secret, code):
            return True
        
        if self.verify_backup_code(user, code):
            return True
        
        return False
    
    def regenerate_backup_codes(self, user: User) -> list[str]:
        """
        Regenerate backup codes for a user.
        Returns new plain backup codes.
        """
        if not user.two_factor_enabled:
            raise ValueError("2FA is not enabled")
        
        plain_codes, hashed_codes = self.generate_backup_codes()
        
        user.backup_codes = hashed_codes
        self.session.add(user)
        self.session.commit()
        
        return plain_codes
    
    def get_2fa_status(self, user: User) -> dict:
        """Get 2FA status for a user."""
        return {
            "enabled": user.two_factor_enabled,
            "has_backup_codes": bool(user.backup_codes and len(user.backup_codes) > 0)
        }
