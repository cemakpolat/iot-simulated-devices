# server/app/api/dependencies.py

"""Updated dependencies with simplified JWT handling"""
from fastapi import Request, HTTPException, Depends
from typing import Generator

# Import JWT functions from the dedicated handler
from .auth.jqt_handler import (
    verify_jwt_token, 
    require_admin, 
    require_user, 
    require_roles,
    #set_jwt_secret,  # Export for use in app startup
    #get_jwt_secret   # Export for use in app startup
      # Export for use in app startup
)

# Import your services and clients
from ..services.thermostat_service import ThermostatControlService
from ..services.prediction_service import PredictionService
from ..services.maintenance_service import MaintenanceService
from ..services.notification_service import NotificationService
from ..database.influxdb_client import InfluxDBClient
from ..database.postgres_client import PostgreSQLClient
from ..database.redis_client import RedisClient
from ..coap.client import EnhancedCoAPClient
from ..security.password_hasher import PasswordHasher
from .models.responses import AuthenticatedUser
from sqlalchemy.orm import Session

# Re-export auth dependencies for convenience
__all__ = [
    "verify_jwt_token", 
    "require_admin", 
    "require_user", 
    "require_roles",
    "set_jwt_secret",
    "get_jwt_secret"
]

# Service Dependencies
def get_thermostat_service(request: Request) -> ThermostatControlService:
    """Get thermostat control service"""
    service = getattr(request.app.state, 'thermostat_service', None)
    if service is None:
        raise HTTPException(status_code=503, detail="Thermostat service not available")
    return service

def get_prediction_service(request: Request) -> PredictionService:
    """Get prediction service"""
    service = getattr(request.app.state, 'prediction_service', None)
    if service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    return service

def get_maintenance_service(request: Request) -> MaintenanceService:
    """Get maintenance service"""
    service = getattr(request.app.state, 'maintenance_service', None)
    if service is None:
        raise HTTPException(status_code=503, detail="Maintenance service not available")
    return service

def get_notification_service(request: Request) -> NotificationService:
    """Get notification service"""
    service = getattr(request.app.state, 'notification_service', None)
    if service is None:
        raise HTTPException(status_code=503, detail="Notification service not available")
    return service

# Database Client Dependencies
def get_influxdb_client(request: Request) -> InfluxDBClient:
    """Get InfluxDB client"""
    client = getattr(request.app.state, 'influx_client', None)
    if client is None:
        raise HTTPException(status_code=503, detail="InfluxDB client not available")
    return client

# def get_postgres_client(request: Request) -> PostgreSQLClient:
#     """Get PostgreSQL client"""
#     client = getattr(request.app.state, 'postgres_client', None)
#     if client is None:
#         raise HTTPException(status_code=503, detail="PostgreSQL client not available")
#     print("test")
#     return client

def get_postgres_client(request: Request) -> PostgreSQLClient:
    """Get PostgreSQL client dependency"""
    client = getattr(request.app.state, 'postgres_client', None)
    if client is None:
        raise HTTPException(status_code=503, detail="PostgreSQL client not available")
    
    # Check if properly initialized
    if client.SessionLocal is None:
        raise HTTPException(status_code=503, detail="PostgreSQL client not properly initialized")
    
    return client

def get_db(request: Request) -> Generator[Session, None, None]:
    """Get database session dependency"""
    postgres_client = get_postgres_client(request)
    db_generator = postgres_client.get_db()
    db = next(db_generator)
    try:
        yield db
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass

def get_redis_client(request: Request) -> RedisClient:
    """Get Redis client"""
    client = getattr(request.app.state, 'redis_client', None)
    if client is None:
        raise HTTPException(status_code=503, detail="Redis client not available")
    return client

def get_coap_client(request: Request) -> EnhancedCoAPClient:
    """Get CoAP client"""
    client = getattr(request.app.state, 'coap_client', None)
    if client is None:
        raise HTTPException(status_code=503, detail="CoAP client not available")
    return client

# Utility Dependencies
def get_password_hasher() -> PasswordHasher:
    """Get password hasher utility"""
    return PasswordHasher()

# Device ownership validation
async def validate_device_ownership(
    device_id: str,
    current_user: AuthenticatedUser = Depends(verify_jwt_token),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client)
) -> str:
    """Validate that the current user owns the specified device"""
    device = await postgres_client.get_device(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this device")
    
    return device_id

# Optional: User data with database lookup
async def get_current_user_with_db(
    current_user: AuthenticatedUser = Depends(verify_jwt_token),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client)
) -> dict:
    """Get current user data from database"""
    user_data = await postgres_client.get_user_by_username(current_user.username)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found in database")
    
    return {
        "id": user_data["id"],
        "username": user_data["username"],
        "email": user_data["email"],
        "roles": current_user.roles,
        "is_active": user_data["is_active"],
        "created_at": user_data["created_at"],
        "last_login_at": user_data.get("last_login_at")
    }

# Role-specific dependencies using the JWT handler
require_admin_role = require_admin
require_user_role = require_user

# Custom role combinations
require_admin_or_moderator = require_roles(["admin", "moderator"])
require_device_manager = require_roles(["admin", "device_manager"])
require_maintenance_access = require_roles(["admin", "maintenance", "technician"])