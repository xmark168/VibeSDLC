from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/db"
    SECRET_KEY: str  # JWT secret
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    # Development Mode
    DEV_MODE: bool = True  # Set to False in production

    # CSRF Protection
    CSRF_SECRET_KEY: Optional[str] = None  # Will use SECRET_KEY if not provided
    CSRF_TOKEN_EXPIRE_MINUTES: int = 60

    # Cookie Settings
    COOKIE_SECURE: bool = False  # Set to True in production with HTTPS
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"  # "strict", "lax", or "none"
    COOKIE_DOMAIN: Optional[str] = None  # Set in production

    class Config:
        env_file = ".env"

settings = Settings()