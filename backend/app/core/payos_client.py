from payos import PayOS
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PayOSClient:
    _instance: Optional[PayOS] = None

    @classmethod
    def get_instance(cls) -> PayOS:
        if cls._instance is None:
            if not all([
                settings.PAYOS_CLIENT_ID,
                settings.PAYOS_API_KEY,
                settings.PAYOS_CHECKSUM_KEY
            ]):
                raise ValueError("PayOS credentials are not properly configured")
            cls._instance = PayOS(
                client_id=settings.PAYOS_CLIENT_ID,
                api_key=settings.PAYOS_API_KEY,
                checksum_key=settings.PAYOS_CHECKSUM_KEY
            )
        return cls._instance


def payos_client() -> PayOS:
    return PayOSClient.get_instance()
