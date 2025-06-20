# app/core/dependencies.py
import logging
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .security import SecurityService
from ..infrastructure.database.postgres import PostgreSQLClient
from ..infrastructure.database.influxdb import InfluxDBClient
from ..infrastructure.database.redis import RedisClient
from ..infrastructure.external.coap_client import EnhancedCoAPClient
from ..services.device_service import DeviceService
from ..services.ml_service import MLService
from ..services.auth_service import AuthService
from ..services.notification_service import NotificationService
from ..repositories.timeseries_repository import TimeseriesRepository
from ..models.database.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

class DependencyManager:
    """Manages application dependencies and their lifecycle."""
    
    def __init__(self):
        self.postgres_client: Optional[PostgreSQLClient] = None
        self.influx_client: Optional[InfluxDBClient] = None
        self.redis_client: Optional[RedisClient] = None
        self.coap_client: Optional[EnhancedCoAPClient] = None
        
        # Services
        self.device_service: Optional[DeviceService] = None
        self.ml_service: Optional[MLService] = None
        self.auth_service: Optional[AuthService] = None
        self.notification_service: Optional[NotificationService] = None
        
        # Repositories
        self.timeseries_repo: Optional[TimeseriesRepository] = None
        
        # Security
        self.security_service = SecurityService(settings.SECRET_KEY)
    
    async def initialize_all(self):
        """Initialize all dependencies in correct order."""
        logger.info("Initializing application dependencies...")
        
        # Initialize infrastructure
        await self._initialize_infrastructure()
        
        # Initialize repositories
        await self._initialize_repositories()
        
        # Initialize services
        await self._initialize_services()
        
        logger.info("All dependencies initialized successfully")
    
    async def _initialize_infrastructure(self):
        """Initialize infrastructure components."""
        self.postgres_client = PostgreSQLClient()
        await self.postgres_client.initialize()
        
        self.influx_client = InfluxDBClient()
        await self.influx_client.initialize()
        
        self.redis_client = RedisClient()
        await self.redis_client.initialize()
        
        self.coap_client = EnhancedCoAPClient()
        await self.coap_client.initialize()
    
    async def _initialize_repositories(self):
        """Initialize repository components."""
        self.timeseries_repo = TimeseriesRepository(self.influx_client)
    
    async def _initialize_services(self):
        """Initialize service components."""
        self.device_service = DeviceService(self.coap_client, self.redis_client)
        await self.device_service.initialize()
        
        self.ml_service = MLService(self.timeseries_repo)
        await self.ml_service.initialize()
        
        self.auth_service = AuthService(self.security_service)
        
        self.notification_service = NotificationService()
        await self.notification_service.initialize()
    
    async def cleanup_all(self):
        """Cleanup all dependencies."""
        logger.info("Cleaning up application dependencies...")
        
        # Cleanup services
        if self.device_service:
            await self.device_service.cleanup()
        if self.ml_service:
            await self.ml_service.cleanup()
        if self.notification_service:
            await self.notification_service.cleanup()
        
        # Cleanup infrastructure
        if self.redis_client:
            await self.redis_client.close()
        if self.influx_client:
            await self.influx_client.close()
        if self.postgres_client:
            await self.postgres_client.close()
        if self.coap_client:
            await self.coap_client.close()
        
        logger.info("All dependencies cleaned up")

# Global dependency manager instance
_dependency_manager: Optional[DependencyManager] = None

def get_dependency_manager() -> DependencyManager:
    """Get global dependency manager."""
    global _dependency_manager
    if _dependency_manager is None:
        _dependency_manager = DependencyManager()
    return _dependency_manager

# FastAPI dependency functions
async def get_db() -> Session:
    """Get database session."""
    manager = get_dependency_manager()
    if not manager.postgres_client:
        raise HTTPException(status_code=500, detail="Database not available")
    
    async for session in manager.postgres_client.get_db():
        yield session

async def get_device_service() -> DeviceService:
    """Get device service."""
    manager = get_dependency_manager()
    if not manager.device_service:
        raise HTTPException(status_code=500, detail="Device service not available")
    return manager.device_service

async def get_ml_service() -> MLService:
    """Get ML service."""
    manager = get_dependency_manager()
    if not manager.ml_service:
        raise HTTPException(status_code=500, detail="ML service not available")
    return manager.ml_service

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    manager = get_dependency_manager()
    if not manager.security_service:
        raise HTTPException(status_code=500, detail="Security service not available")
    
    try:
        payload = manager.security_service.decode_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )