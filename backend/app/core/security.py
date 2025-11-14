from datetime import datetime, timedelta
from jose import JWTError
import jwt
from passlib.context import CryptContext
import bcrypt
import secrets
import hashlib
from app.core.config import settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password với bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Tạo JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token() -> tuple[str, str]:
    """
    Tạo refresh token và hash của nó
    Pre-hash với SHA256 trước khi hash với bcrypt để tránh giới hạn 72 bytes
    """
    token = secrets.token_urlsafe(64)  # 64 bytes ~ 86 chars
    # Pre-hash token với SHA256 vì bcrypt chỉ hỗ trợ tối đa 72 bytes
    token_prehash = hashlib.sha256(token.encode()).hexdigest()
    token_hash = bcrypt.hashpw(token_prehash.encode(), bcrypt.gensalt()).decode()
    return token, token_hash

def verify_refresh_token(stored_hash: str, provided_token: str) -> bool:
    """
    Verify refresh token với hash đã lưu
    Pre-hash với SHA256 trước khi verify với bcrypt
    """
    # Pre-hash token giống như lúc tạo
    token_prehash = hashlib.sha256(provided_token.encode()).hexdigest()
    return bcrypt.checkpw(token_prehash.encode(), stored_hash.encode())

def create_email_verification_token(email: str) -> str:
    """Token xác thực email"""
    expire = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": email, "exp": expire, "type": "email_verify"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def decode_access_token(token: str) -> dict:
    """Decode và verify JWT access token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise JWTError("Token has expired")
    except jwt.InvalidTokenError:
        raise JWTError("Invalid token")