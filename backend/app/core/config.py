import os
import warnings
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
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


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


def load_env_file():
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
            load_dotenv(dotenv_path=env_file, override=True)
            print(f"Loaded environment from {env_file}")
            return str(env_file)

    return None


ENV_FILE = load_env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "VibeSDLC"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "VibeSDLC unified services"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "development", "staging", "production", "test"] = (
        "local"
    )
    DEBUG: bool = False

    # SECURITY SETTINGS
    SECRET_KEY: str = Field(
        default=...,  # Required - must be set in environment
        description="Secret key for JWT encoding. Must be at least 32 characters."
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days

    # OAUTH SETTINGS
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""

    # CORS SETTINGS
    FRONTEND_HOST: str = "http://localhost:5173"
    BACKEND_HOST: str = "http://localhost:8000"
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    @computed_field
    @property
    def oauth_callback_url(self) -> str:
        return f"{self.BACKEND_HOST.rstrip('/')}{self.API_V1_STR}/oauth-callback"

    @computed_field
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    # DATABASE SETTINGS
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

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
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEST_USER: EmailStr = "test@example.com"

    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    # Anthropic API Settings (all agents use this)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_API_BASE: str = "https://api.anthropic.com"

    SENTRY_DSN: HttpUrl | None = None

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_URL: str | None = None

    @computed_field
    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL

        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_ENABLE_AUTO_COMMIT: bool = True
    KAFKA_AUTO_OFFSET_RESET: Literal["earliest", "latest"] = "latest"
    KAFKA_GROUP_ID: str = "vibes_agents"
    KAFKA_SASL_MECHANISM: str | None = None
    KAFKA_SASL_USERNAME: str | None = None
    KAFKA_SASL_PASSWORD: str | None = None
    KAFKA_SECURITY_PROTOCOL: Literal[
        "PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"
    ] = "PLAINTEXT"

    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    LANGFUSE_ENABLED: bool = True

    # AGENT POOL SETTINGS
    AGENT_POOL_MAX_AGENTS: int = 100
    AGENT_POOL_HEALTH_CHECK_INTERVAL: int = 60
    AGENT_POOL_AUTO_SCALE_ENABLED: bool = True
    AGENT_POOL_AUTO_SCALE_THRESHOLD: float = 0.8
    AGENT_POOL_USE_ROLE_SPECIFIC: bool = True
    AGENT_POOL_ROLE_CONFIGS: dict = Field(default_factory=lambda: {
        "team_leader": {"max_agents": 20, "priority": 1},
        "developer": {"max_agents": 50, "priority": 2},
        "tester": {"max_agents": 30, "priority": 2},
        "business_analyst": {"max_agents": 20, "priority": 1},
    })

    # AGENT HEALTH CHECK SETTINGS
    AGENT_HEALTH_MAX_CONSECUTIVE_FAILURES: int = 20     # Terminate after 20 consecutive failures
    AGENT_HEALTH_STALE_BUSY_TIMEOUT_SECONDS: int = 1800 # 30 min busy without activity = stale
    AGENT_HEALTH_WARNING_THRESHOLD: int = 15            # Log warning after 15 failures

    # METRICS SETTINGS
    METRICS_FLUSH_INTERVAL: int = 10
    METRICS_BUFFER_SIZE: int = 100

    # PAYOS PAYMENT GATEWAY SETTINGS
    PAYOS_CLIENT_ID: str = ""
    PAYOS_API_KEY: str = ""
    PAYOS_CHECKSUM_KEY: str = ""
    PAYOS_WEBHOOK_SECRET: str = ""

    # SEPAY PAYMENT GATEWAY SETTINGS
    SEPAY_API_KEY: str = ""
    SEPAY_BANK_CODE: str = "MBBank"
    SEPAY_ACCOUNT_NUMBER: str = "0377580457"
    SEPAY_API_URL: str = "https://my.sepay.vn/userapi"

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
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
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        return self


settings = Settings()

# Document Upload Configuration
DOCUMENT_UPLOAD_LIMITS = {
    "max_file_size": 10 * 1024 * 1024,  # 10 MB
    "max_text_length": 50_000,  # 50K characters after extraction (safe for LLM)
    "allowed_extensions": [".docx", ".txt"],  # Word and plain text
    "max_files_per_message": 1,
}
