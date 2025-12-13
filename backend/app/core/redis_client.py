import json
from typing import Any, Optional
import redis
from app.core.config import settings


class RedisClient:
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    def connect(self) -> bool:
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
            self._client.ping()
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False
    
    def disconnect(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            finally:
                self._client = None
                self._connected = False
    
    def is_connected(self) -> bool:
        if not self._connected or not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
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
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        if not self.is_connected():
            if not self.connect():
                return None
        try:
            value = self._client.get(key)
            if value is None:
                return None
            if isinstance(value, str) and value.strip() and value.strip()[0] in ('{', '['):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception:
            return None
    
    def delete(self, key: str) -> bool:
        if not self.is_connected():
            if not self.connect():
                return False
        try:
            return bool(self._client.delete(key))
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        if not self.is_connected():
            if not self.connect():
                return False
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False
    
    def ttl(self, key: str) -> int:
        if not self.is_connected():
            if not self.connect():
                return -2
        try:
            return self._client.ttl(key)
        except Exception:
            return -2


redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    return redis_client
