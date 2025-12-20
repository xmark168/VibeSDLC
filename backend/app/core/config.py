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
    DESCRIPTION: str = "VibeSDLC services"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "development", "staging", "production", "test"] = (
        "local"
    )
    DEBUG: bool = False

    # SECURITY SETTINGS
    SECRET_KEY: str = Field(
        default=..., 
        description="Secret key"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # day

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
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        return self


# ============================================================================
# GROUPED SETTINGS CLASSES
# ============================================================================

class LLMSettings(BaseSettings):
    """LLM and AI model configuration."""
    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")
    
    # Provider Selection
    PROVIDER: Literal["anthropic", "openrouter"] = Field(
        default="anthropic", 
        description="LLM provider: anthropic or openrouter"
    )
    
    # Anthropic API Configuration
    API_KEY: str = Field(default="", description="Anthropic API key")
    API_BASE: str = Field(default="https://api.anthropic.com", description="API base URL")
    
    # OpenRouter Configuration (used when PROVIDER=openrouter)
    OPENROUTER_API_KEY: str = Field(
        default="", 
        description="OpenRouter API key"
    )
    OPENROUTER_API_BASE: str = Field(
        default="https://openrouter.ai/api/v1", 
        description="OpenRouter API base URL"
    )
    
    # Default LLM Parameters
    DEFAULT_TEMPERATURE: float = Field(default=0.2, description="Default temperature for LLM")
    DEFAULT_MAX_TOKENS: int = Field(default=16384, description="Default max tokens")
    DEFAULT_TIMEOUT: int = Field(default=60, description="Default timeout in seconds")
    
    # Retry Settings
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    RETRY_BACKOFF_MIN: int = Field(default=1, description="Minimum backoff in seconds")
    RETRY_BACKOFF_MAX: int = Field(default=10, description="Maximum backoff in seconds")
    
    # Parallel Execution
    MAX_CONCURRENT_TASKS: int = Field(default=10, description="Max concurrent tasks")
    
    # Debug/Fix Loops
    MAX_DEBUG_ATTEMPTS: int = Field(default=3, description="Max debug attempts")
    MAX_DEBUG_REVIEWS_DEVELOPER: int = Field(default=3, description="Max developer reviews")
    MAX_DEBUG_REVIEWS_TESTER: int = Field(default=2, description="Max tester reviews")
    
    # Test Generation Limits
    MAX_SCENARIOS_UNIT: int = Field(default=2, description="Max unit test scenarios")
    MAX_SCENARIOS_INTEGRATION: int = Field(default=3, description="Max integration test scenarios")
    MAX_REVIEW_CYCLES: int = Field(default=2, description="Max review cycles")
    MAX_LBTM_PER_FILE: int = Field(default=2, description="Max LBTM per file")


class RouterSettings(BaseSettings):
    """Message router and context management configuration."""
    model_config = SettingsConfigDict(env_prefix="ROUTER_", extra="ignore")
    
    # Context Timeouts
    CONTEXT_TIMEOUT_ONLINE_MINUTES: int = Field(
        default=7, 
        description="Context timeout when user is online (WebSocket active)"
    )
    CONTEXT_TIMEOUT_OFFLINE_MINUTES: int = Field(
        default=15, 
        description="Context timeout when user is offline"
    )
    GRACE_PERIOD_SECONDS: int = Field(
        default=120, 
        description="Grace period after disconnect before timeout applies"
    )


class DocumentUploadSettings(BaseSettings):
    """Document upload and processing configuration."""
    model_config = SettingsConfigDict(env_prefix="DOCUMENT_", extra="ignore")
    
    MAX_FILE_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum file size in bytes"
    )
    MAX_TEXT_LENGTH: int = Field(
        default=50_000,
        description="Maximum text length after extraction"
    )
    ALLOWED_EXTENSIONS: list[str] = Field(
        default_factory=lambda: [".docx", ".txt"],
        description="Allowed file extensions"
    )
    MAX_FILES_PER_MESSAGE: int = Field(
        default=1,
        description="Maximum files per message"
    )


class RedisSettings(BaseSettings):
    """Redis connection and client configuration."""
    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")
    
    HOST: str = Field(default="localhost", description="Redis host")
    PORT: int = Field(default=6379, description="Redis port")
    PASSWORD: str | None = Field(default=None, description="Redis password")
    DB: int = Field(default=0, description="Redis database number")
    URL: str | None = Field(default=None, description="Redis URL (overrides other settings)")
    
    # Connection Settings
    SOCKET_CONNECT_TIMEOUT: int = Field(default=5, description="Socket connect timeout in seconds")
    SOCKET_TIMEOUT: int = Field(default=5, description="Socket timeout in seconds")
    RETRY_ON_TIMEOUT: bool = Field(default=True, description="Retry on timeout")
    
    @computed_field
    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        if self.URL:
            return self.URL
        auth = f":{self.PASSWORD}@" if self.PASSWORD else ""
        return f"redis://{auth}{self.HOST}:{self.PORT}/{self.DB}"


class KafkaSettings(BaseSettings):
    """Kafka broker and topic configuration."""
    model_config = SettingsConfigDict(env_prefix="KAFKA_", extra="ignore")
    
    # Broker Configuration
    BOOTSTRAP_SERVERS: str = Field(default="localhost:9092", description="Kafka bootstrap servers")
    ENABLE_AUTO_COMMIT: bool = Field(default=True, description="Enable auto commit")
    AUTO_OFFSET_RESET: Literal["earliest", "latest"] = Field(
        default="latest",
        description="Auto offset reset"
    )
    GROUP_ID: str = Field(default="vibes_agents", description="Consumer group ID")
    
    # Security
    SASL_MECHANISM: str | None = Field(default=None, description="SASL mechanism")
    SASL_USERNAME: str | None = Field(default=None, description="SASL username")
    SASL_PASSWORD: str | None = Field(default=None, description="SASL password")
    SECURITY_PROTOCOL: Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"] = Field(
        default="PLAINTEXT",
        description="Security protocol"
    )
    
    # Topic Management Timeouts
    LIST_TOPICS_TIMEOUT: float = Field(default=2.0, description="List topics timeout in seconds")
    CREATE_TOPICS_TIMEOUT: int = Field(default=5, description="Create topics timeout in seconds")
    FUTURE_RESULT_TIMEOUT: int = Field(default=5, description="Future result timeout in seconds")
    
    # Topic Configuration
    HIGH_TRAFFIC_PARTITIONS: int = Field(default=6, description="Partitions for high-traffic topics")
    DEFAULT_PARTITIONS: int = Field(default=3, description="Default partitions for topics")
    REPLICATION_FACTOR: int = Field(default=1, description="Replication factor")
    DEFAULT_RETENTION_MS: int = Field(
        default=7 * 24 * 60 * 60 * 1000,  # 7 days
        description="Default retention in milliseconds"
    )


class ProjectContextSettings(BaseSettings):
    """Project context and caching configuration."""
    model_config = SettingsConfigDict(env_prefix="PROJECT_CONTEXT_", extra="ignore")
    
    KANBAN_CACHE_TTL: int = Field(default=30, description="Kanban cache TTL in seconds")
    SUMMARY_THRESHOLD: int = Field(default=5, description="Messages before summarization")


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    model_config = SettingsConfigDict(env_prefix="LOGGING_", extra="ignore")
    
    MAX_BYTES: int = Field(default=10 * 1024 * 1024, description="Max bytes per log file")
    BACKUP_COUNT: int = Field(default=5, description="Number of backup files")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")


class DatabaseSettings(BaseSettings):
    """Database connection and pool configuration."""
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")
    
    SERVER: str = Field(description="PostgreSQL server host")
    PORT: int = Field(default=5433, description="PostgreSQL port")
    USER: str = Field(description="PostgreSQL user")
    PASSWORD: str = Field(default="", description="PostgreSQL password")
    DB: str = Field(default="", description="PostgreSQL database name")
    
    # Thread Pool Configuration
    DB_EXECUTOR_MAX_WORKERS: int = Field(default=10, description="Max database executor workers")
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow connections")
    
    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """Build SQLAlchemy database URI."""
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.USER,
            password=self.PASSWORD,
            host=self.SERVER,
            port=self.PORT,
            path=self.DB,
        )


class MinIOSettings(BaseSettings):
    """MinIO object storage configuration."""
    model_config = SettingsConfigDict(env_prefix="MINIO_", extra="ignore")
    
    ENDPOINT: str = Field(default="localhost:9000", description="MinIO endpoint")
    ACCESS_KEY: str = Field(default="minioadmin", description="MinIO access key")
    SECRET_KEY: str = Field(default="minioadmin", description="MinIO secret key")
    SECURE: bool = Field(default=False, description="Use HTTPS for MinIO")
    BUCKET_NAME: str = Field(default="images", description="MinIO bucket name")


# ============================================================================
# SETTINGS INSTANCES
# ============================================================================

settings = Settings()
llm_settings = LLMSettings()
router_settings = RouterSettings()
document_upload_settings = DocumentUploadSettings()
redis_settings = RedisSettings()
kafka_settings = KafkaSettings()
project_context_settings = ProjectContextSettings()
logging_settings = LoggingSettings()
database_settings = DatabaseSettings()
minio_settings = MinIOSettings()
