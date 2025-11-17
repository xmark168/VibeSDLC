"""Application configuration management.

This module handles environment-specific configuration loading, parsing, and management
for the application. It includes environment detection, .env file loading, and
configuration value parsing.
"""

import os
import secrets
import warnings
from enum import Enum
from typing import Annotated, Any, Literal
from pathlib import Path

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    Field,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self
from dotenv import load_dotenv


# HELPER FUNCTIONS
def parse_cors(v: Any) -> list[str] | str:
    """Parse CORS origins from various formats."""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


def load_env_file():
    """Load environment-specific .env file with priority."""
    env_value = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "local"))
    base_dir = Path(__file__).parent.parent.parent

    env_files = [
        base_dir / f".env.{env_value}.local",
        base_dir / f".env.{env_value}",
        base_dir / ".env.local",
        base_dir / ".env",
    ]

    for env_file in env_files:
        if env_file.is_file():
            load_dotenv(dotenv_path=env_file)
            print(f"Loaded environment from {env_file}")
            return str(env_file)

    return None


# Load env file before settings initialization
ENV_FILE = load_env_file()


# SETTINGS CLASS
class Settings(BaseSettings):
    """Unified application settings with pydantic validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    # GENERAL APPLICATION SETTINGS
    PROJECT_NAME: str = "VibeSDLC"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "VibeSDLC unified services"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "development", "staging", "production", "test"] = (
        "local"
    )
    DEBUG: bool = False

    # SECURITY SETTINGS
    SECRET_KEY: str = Field(default="your-fixed-secret-key-min-32-chars-change-this-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days

    # CORS SETTINGS
    FRONTEND_HOST: str = "http://localhost:5173"
    BACKEND_CORS_ORGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    @computed_field
    @property
    def all_cors_origins(self) -> list[str]:
        """Compute all CORS origins including frontend host."""
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORGINS] + [
            self.FRONTEND_HOST
        ]

    # DATABASE SETTINGS (from management-service)
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """Build PostgreSQL connection URI"""
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # EMAIL SETTINGS (from management-service)
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @computed_field
    @property
    def emails_enabled(self) -> bool:
        """Check if email functionality is enabled."""
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEST_USER: EmailStr = "test@example.com"

    # USER SETTINGS
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    # LLM/LANGGRAPH SETTINGS
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    DEFAULT_LLM_TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 2000
    MAX_LLM_CALL_RETRIES: int = 3

    # OPENAI API KEY (for CrewAI - synced with LLM_API_KEY)
    OPENAI_API_KEY: str = ""

    # MONITORING
    SENTRY_DSN: HttpUrl | None = None

    # REDIS SETTINGS
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_URL: str | None = None

    @computed_field
    @property
    def redis_url(self) -> str:
        """Build Redis connection URL"""
        if self.REDIS_URL:
            return self.REDIS_URL

        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # KAFKA SETTINGS (for CrewAI event-driven architecture)
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_ENABLE_AUTO_COMMIT: bool = True
    KAFKA_AUTO_OFFSET_RESET: Literal["earliest", "latest"] = "latest"
    KAFKA_GROUP_ID: str = "crewai_agents"
    KAFKA_SASL_MECHANISM: str | None = None
    KAFKA_SASL_USERNAME: str | None = None
    KAFKA_SASL_PASSWORD: str | None = None
    KAFKA_SECURITY_PROTOCOL: Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"] = "PLAINTEXT"

    # VALIDATORS
    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        """Set default email from name if not provided."""
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    @model_validator(mode="after")
    def _sync_openai_api_key(self) -> Self:
        """Sync OPENAI_API_KEY with LLM_API_KEY for CrewAI compatibility."""
        if not self.OPENAI_API_KEY and self.LLM_API_KEY:
            self.OPENAI_API_KEY = self.LLM_API_KEY
        return self

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        """Check if default secrets are being used in production."""
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        """Enforce that default secrets are not used in production."""
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        return self


# SINGLETON INSTANCE
settings = Settings()
