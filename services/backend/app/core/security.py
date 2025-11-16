from datetime import datetime, timedelta, timezone
from typing import Any
import secrets

import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"

def create_access_token(
    subject: str | Any,
    expires_delta: timedelta,
    token_type: str = "access"
) -> str:
    """
    Create JWT access token with comprehensive claims

    Args:
        subject: User ID (sub claim)
        expires_delta: Token expiration time delta
        scopes: List of permissions/scopes
        token_type: Token type ("access" or "refresh")

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode = {
        "sub": str(subject),                # Subject (user ID)
        "exp": int(expire.timestamp()),     # Expiration time
        "iat": int(now.timestamp()),        # Issued at
        "nbf": int(now.timestamp()),        # Not before
        "type": token_type,                 # Token type
    }

    # Add JWT ID for access tokens (for potential revocation)
    if token_type == "access":
        to_encode["jti"] = secrets.token_urlsafe(16)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify JWT access token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.JWTError: If token is invalid or expired
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM]
    )
    return payload


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # Truncate password to 72 bytes max for bcrypt compatibility
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate at byte level and decode back to string
        password_bytes = password_bytes[:72]
        # Handle potential incomplete UTF-8 characters at the end
        password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(password)