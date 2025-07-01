"""Redis client for caching and real-time data"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for caching, sessions, and real-time data"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.client = None
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.from_url(self.redis_url)
            
            # Test connection
            await self.client.ping()
            logger.info("Connected to Redis successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        if not self.client: return
        try:
            await self.client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Error setting to Redis key {key}: {e}", exc_info=True)    
    async def get(self, key: str, as_json: bool = False) -> Optional[Any]:
        """Get value by key"""
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            value = value.decode('utf-8')
            if as_json:
                return json.loads(value)
            return value
        except Exception as e:
            logger.error(f"Error getting Redis key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete a key"""
        try:
            result = await self.client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting Redis key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            result = await self.client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking Redis key existence {key}: {e}")
            return False
    
    # Device status caching
    async def cache_device_status(self, device_id: str, status: Dict[str, Any], ttl: int = 300) -> bool:
        """Cache device status for quick access"""
        key = f"device_status:{device_id}"
        status['cached_at'] = datetime.now().isoformat()
        return await self.set(key, status, ttl)
    
    async def get_cached_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get cached device status"""
        key = f"device_status:{device_id}"
        return await self.get(key, as_json=True)
    
    # Sensor data caching
    async def cache_latest_sensor_data(self, device_id: str, sensor_data: Dict[str, Any], ttl: int = 60) -> bool:
        """Cache latest sensor readings"""
        key = f"sensor_data:{device_id}:latest"
        sensor_data['cached_at'] = datetime.now().isoformat()
        return await self.set(key, sensor_data, ttl)
    
    async def get_cached_sensor_data(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get cached sensor data"""
        key = f"sensor_data:{device_id}:latest"
        return await self.get(key, as_json=True)
    
    # ML predictions caching
    async def cache_predictions(self, device_id: str, predictions: List[float], 
                              prediction_type: str = "temperature", ttl: int = 1800) -> bool:
        """Cache ML predictions"""
        key = f"predictions:{device_id}:{prediction_type}"
        prediction_data = {
            'predictions': predictions,
            'generated_at': datetime.now().isoformat(),
            'type': prediction_type
        }
        return await self.set(key, prediction_data, ttl)
    
    async def get_cached_predictions(self, device_id: str, prediction_type: str = "temperature") -> Optional[Dict[str, Any]]:
        """Get cached predictions"""
        key = f"predictions:{device_id}:{prediction_type}"
        return await self.get(key, as_json=True)
    
    # User session management
    async def create_user_session(self, user_id: int, session_data: Dict[str, Any], ttl: int = 86400) -> str:
        """Create user session"""
        session_id = f"session:{user_id}:{datetime.now().timestamp()}"
        session_data.update({
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        })
        await self.set(session_id, session_data, ttl)
        return session_id
    
    async def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session"""
        return await self.get(session_id, as_json=True)
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity"""
        session = await self.get_user_session(session_id)
        if session:
            session['last_activity'] = datetime.now().isoformat()
            return await self.set(session_id, session, 86400)  # Reset TTL
        return False
    
    async def delete_user_session(self, session_id: str) -> bool:
        """Delete user session"""
        return await self.delete(session_id)
    
    # Rate limiting
    async def check_rate_limit(self, identifier: str, limit: int, window: int) -> bool:
        """Check if request is within rate limit"""
        try:
            key = f"rate_limit:{identifier}"
            current = await self.client.get(key)
            
            if current is None:
                await self.client.setex(key, window, 1)
                return True
            
            current_count = int(current)
            if current_count >= limit:
                return False
            
            await self.client.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow request on error
    
    # Device control state
    async def set_device_control_state(self, device_id: str, control_data: Dict[str, Any], ttl: int = 300) -> bool:
        """Set device control state"""
        key = f"control_state:{device_id}"
        control_data['set_at'] = datetime.now().isoformat()
        return await self.set(key, control_data, ttl)
    
    async def get_device_control_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device control state"""
        key = f"control_state:{device_id}"
        return await self.get(key, as_json=True)
    
    # Alert management
    async def add_alert_to_queue(self, alert_data: Dict[str, Any]) -> bool:
        """Add alert to processing queue"""
        try:
            queue_key = "alert_queue"
            alert_data['queued_at'] = datetime.now().isoformat()
            await self.client.lpush(queue_key, json.dumps(alert_data))
            return True
        except Exception as e:
            logger.error(f"Error adding alert to queue: {e}")
            return False
    
    async def get_alert_from_queue(self) -> Optional[Dict[str, Any]]:
        """Get alert from processing queue"""
        try:
            queue_key = "alert_queue"
            alert_json = await self.client.rpop(queue_key)
            if alert_json:
                return json.loads(alert_json.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Error getting alert from queue: {e}")
            return None
    
    async def get_queue_size(self, queue_name: str = "alert_queue") -> int:
        """Get queue size"""
        try:
            return await self.client.llen(queue_name)
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0
    
    # Pub/Sub for real-time updates
    async def publish_device_update(self, device_id: str, update_data: Dict[str, Any]) -> bool:
        """Publish device update to subscribers"""
        try:
            channel = f"device_updates:{device_id}"
            update_data['published_at'] = datetime.now().isoformat()
            await self.client.publish(channel, json.dumps(update_data))
            return True
        except Exception as e:
            logger.error(f"Error publishing device update: {e}")
            return False
    
    async def subscribe_to_device_updates(self, device_id: str):
        """Subscribe to device updates"""
        try:
            pubsub = self.client.pubsub()
            channel = f"device_updates:{device_id}"
            await pubsub.subscribe(channel)
            return pubsub
        except Exception as e:
            logger.error(f"Error subscribing to device updates: {e}")
            return None
    
    # Statistics and monitoring
    async def increment_counter(self, counter_name: str, amount: int = 1) -> int:
        """Increment a counter"""
        try:
            key = f"counter:{counter_name}"
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing counter {counter_name}: {e}")
            return 0
    
    async def get_counter(self, counter_name: str) -> int:
        """Get counter value"""
        try:
            key = f"counter:{counter_name}"
            value = await self.client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Error getting counter {counter_name}: {e}")
            return 0
    
    async def set_counter(self, counter_name: str, value: int) -> bool:
        """Set counter value"""
        try:
            key = f"counter:{counter_name}"
            await self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Error setting counter {counter_name}: {e}")
            return False
    
    # Health and maintenance
    async def get_redis_info(self) -> Dict[str, Any]:
        """Get Redis server information"""
        try:
            info = await self.client.info()
            return {
                'version': info.get('redis_version'),
                'uptime': info.get('uptime_in_seconds'),
                'connected_clients': info.get('connected_clients'),
                'used_memory': info.get('used_memory_human'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses')
            }
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return {}
    
    async def flush_cache(self, pattern: str = None) -> bool:
        """Flush cache entries matching pattern"""
        try:
            if pattern:
                keys = await self.client.keys(pattern)
                if keys:
                    await self.client.delete(*keys)
                    logger.info(f"Flushed {len(keys)} keys matching pattern {pattern}")
            else:
                await self.client.flushdb()
                logger.info("Flushed entire Redis database")
            return True
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")