import json
import logging
from typing import Any, Optional, Dict, List, Union
import redis.asyncio as redis
from ...core.config import get_settings
from ...core.exceptions import DatabaseError
logger = logging.getLogger(name)
settings = get_settings()
class RedisClient:
    """Enhanced Redis client with connection pooling."""
    def __init__(self):
        self.client = None
        self.connection_pool = None
        self._initialized = False
        self.config = settings.redis_config

    async def initialize(self):
        """Initialize Redis client with connection pooling."""
        try:
            self.connection_pool = redis.ConnectionPool.from_url(
                self.config["url"],
                **{k: v for k, v in self.config.items() if k != "url"}
            )
            
            self.client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.client.ping()
            
            self._initialized = True
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise DatabaseError(f"Redis initialization failed: {str(e)}")

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self._initialized:
            raise DatabaseError("Redis client not initialized")
        
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> bool:
        """Set key-value pair with optional expiration."""
        if not self._initialized:
            raise DatabaseError("Redis client not initialized")
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            elif not isinstance(value, str):
                value = str(value)
            
            result = await self.client.set(key, value, ex=ex, nx=nx)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def get_json(self, key: str) -> Optional[Union[Dict, List]]:
        """Get and deserialize JSON value."""
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key {key}: {e}")
            return None

    async def set_json(self, key: str, value: Union[Dict, List], ex: Optional[int] = None) -> bool:
        """Serialize and set JSON value."""
        try:
            json_str = json.dumps(value, default=str)
            return await self.set(key, json_str, ex=ex)
        except Exception as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key."""
        if not self._initialized:
            return False
        
        try:
            result = await self.client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def close(self):
        """Close Redis client."""
        if self.client:
            await self.client.close()
            logger.info("Redis client closed")