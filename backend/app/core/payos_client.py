"""PayOS Payment Gateway Client"""

from payos import PayOS
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PayOSClient:
    """Singleton PayOS client for payment operations"""
    _instance: Optional[PayOS] = None

    @classmethod
    def get_instance(cls) -> PayOS:
        """Get or create PayOS client instance"""
        if cls._instance is None:
            if not all([
                settings.PAYOS_CLIENT_ID,
                settings.PAYOS_API_KEY,
                settings.PAYOS_CHECKSUM_KEY
            ]):
                logger.warning("PayOS credentials not configured")
                raise ValueError("PayOS credentials are not properly configured")

            cls._instance = PayOS(
                client_id=settings.PAYOS_CLIENT_ID,
                api_key=settings.PAYOS_API_KEY,
                checksum_key=settings.PAYOS_CHECKSUM_KEY
            )
            logger.info("PayOS client initialized successfully")

        return cls._instance


def payos_client() -> PayOS:
    """Get PayOS client instance"""
    return PayOSClient.get_instance()
