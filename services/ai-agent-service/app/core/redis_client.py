"""Redis client configuration and utilities."""

import json
import logging
from typing import Any, Optional
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper with connection management."""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to Redis server."""
        if self._connected and self._client:
            return True
            
        try:
            self._client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self._client.ping()
            self._connected = True
            logger.info("Redis connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Redis server."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Redis: {e}")
            finally:
                self._client = None
                self._connected = False
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self._connected or not self._client:
            return False
        
        try:
            self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a key-value pair with optional TTL."""
        if not self.is_connected():
            if not self.connect():
                return False
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if ttl:
                return self._client.setex(key, ttl, value)
            else:
                return self._client.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        if not self.is_connected():
            if not self.connect():
                return None
        
        try:
            value = self._client.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self.is_connected():
            if not self.connect():
                return False
        
        try:
            return bool(self._client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.is_connected():
            if not self.connect():
                return False
        
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """Get TTL of a key."""
        if not self.is_connected():
            if not self.connect():
                return -2
        
        try:
            return self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error: {e}")
            return -2

# Global Redis client instance
redis_client = RedisClient()

def get_redis_client() -> RedisClient:
    """Get the global Redis client instance."""
    return redis_client
