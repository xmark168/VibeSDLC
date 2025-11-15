"""Kafka configuration for VibeSDLC"""

from pydantic_settings import BaseSettings
from typing import List


class KafkaSettings(BaseSettings):
    """Kafka configuration settings"""

    # Kafka broker settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CLIENT_ID: str = "vibesdlc-backend"

    # Producer settings
    KAFKA_PRODUCER_ACKS: str = "all"  # Wait for all replicas
    KAFKA_PRODUCER_RETRIES: int = 3
    KAFKA_PRODUCER_COMPRESSION_TYPE: str = "gzip"

    # Consumer settings
    KAFKA_CONSUMER_GROUP_ID: str = "vibesdlc-consumers"
    KAFKA_CONSUMER_AUTO_OFFSET_RESET: str = "earliest"  # Start from beginning if no offset
    KAFKA_CONSUMER_ENABLE_AUTO_COMMIT: bool = True
    KAFKA_CONSUMER_AUTO_COMMIT_INTERVAL_MS: int = 1000

    # Connection settings
    KAFKA_CONNECTION_TIMEOUT_MS: int = 10000
    KAFKA_REQUEST_TIMEOUT_MS: int = 30000

    # Enable/Disable Kafka
    KAFKA_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env file


kafka_settings = KafkaSettings()
