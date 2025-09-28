from typing import Any, Dict, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Agent Service"
    ENVIRONMENT: str = "local"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3.5-sonnet-20241022"

    # LangFuse Configuration
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_GROUP_ID: str = "ai-agent-service"

    # Vector Database
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    @field_validator("KAFKA_BOOTSTRAP_SERVERS")
    @classmethod
    def assemble_kafka_servers(cls, v: str) -> str:
        if isinstance(v, str):
            return v
        return v


settings = Settings()