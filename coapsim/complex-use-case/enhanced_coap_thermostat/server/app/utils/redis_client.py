# server/app/utils/redis_client.py
import redis.asyncio as redis # For async Redis operations
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
        self._connect()

    def _connect(self):
        try:
            # Use from_url for easy parsing of redis:// URL
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Redis client initialized for {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            self.client = None

    async def get(self, key: str) -> Optional[str]:
        if not self.client: return None
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Error getting from Redis key {key}: {e}", exc_info=True)
            return None

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        if not self.client: return
        try:
            await self.client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Error setting to Redis key {key}: {e}", exc_info=True)
    
    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Redis client closed.")