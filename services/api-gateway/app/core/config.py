from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # API Gateway Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "VibeSDLC API Gateway"
    ENVIRONMENT: str = "local"

    # Service URLs
    MANAGEMENT_SERVICE_URL: str = "http://management-service:8000"
    AI_AGENT_SERVICE_URL: str = "http://ai-agent-service:8001"

    # For local development
    MANAGEMENT_SERVICE_URL_LOCAL: str = "http://localhost:8000"
    AI_AGENT_SERVICE_URL_LOCAL: str = "http://localhost:8001"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:5173",
        "https://localhost",
        "https://localhost:5173",
    ]

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    REDIS_URL: str = "redis://redis:6379"

    # Security
    SECRET_KEY: str = "changethis"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    def get_management_service_url(self) -> str:
        """Get management service URL based on environment."""
        if self.ENVIRONMENT == "local":
            return self.MANAGEMENT_SERVICE_URL_LOCAL
        return self.MANAGEMENT_SERVICE_URL

    def get_ai_agent_service_url(self) -> str:
        """Get AI agent service URL based on environment."""
        if self.ENVIRONMENT == "local":
            return self.AI_AGENT_SERVICE_URL_LOCAL
        return self.AI_AGENT_SERVICE_URL


settings = Settings()