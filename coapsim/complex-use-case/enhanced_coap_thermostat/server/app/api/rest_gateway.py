# server/app/api/rest_gateway.py
import jwt
import time
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status, Request, Form, Header, Response, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from prometheus_client import generate_latest 

# Import services and clients
from ..services.thermostat_service import ThermostatControlService
from ..services.prediction_service import PredictionService
from ..services.maintenance_service import MaintenanceService
from ..database.influxdb_client import InfluxDBClient
from ..coap.client import EnhancedCoAPClient
from ..config import ServerConfig

from sqlalchemy.orm import Session # For SQLAlchemy session type hint
from ..database.postgres_client import PostgreSQLClient
from ..security.password_hasher import PasswordHasher
from ..database.models import User 
from ..utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Smart Thermostat AI API", version="2.0.0")

# Security schema for JWT
security = HTTPBearer()

# Pydantic models for request/response bodies
class ThermostatCommand(BaseModel):
    action: str 
    target_temperature: Optional[float] = None
    mode: Optional[str] = None
    fan_speed: Optional[str] = None

class ScheduleEntry(BaseModel):
    time: str
    temperature: float
    days: List[str]
    enabled: bool = True

# --- NEW: Pydantic model for Login Request Body (for /auth/login) ---
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel): 
    username: str
    email: str
    password: str

class AuthenticatedUser(BaseModel):
    id: str # Corresponds to 'sub' in JWT
    username: str
    roles: List[str] = [] # Ensure roles is a list, default to empty
 

# --- Dependency Injection (Services will be injected via FastAPI's state) ---
# These functions define how dependencies are obtained for endpoints.
# The actual instances are set in main.py's startup event.
def get_thermostat_service(request: Request) -> ThermostatControlService:
    return request.app.state.thermostat_service

def get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service

def get_maintenance_service(request: Request) -> MaintenanceService:
    return request.app.state.maintenance_service

def get_influxdb_client(request: Request) -> InfluxDBClient:
    return request.app.state.influx_client

def get_coap_client(request: Request) -> EnhancedCoAPClient:
    return request.app.state.coap_client

# --- NEW: Dependency for PostgreSQL Session and PasswordHasher ---
# These depend on instances initialized in main.py and stored in app.state
def get_postgres_client_instance(request: Request) -> PostgreSQLClient:
    return request.app.state.postgres_client # Returns the client instance

def get_postgres_db_session(request: Request) -> Session:
    """Provides a database session for PostgreSQL endpoints."""
    # This yields a session from the PostgreSQLClient instance stored in app.state
    # The yield means the session is closed automatically after the request.
    yield from request.app.state.postgres_client.get_db()

def get_password_hasher() -> PasswordHasher:
    return PasswordHasher() # PasswordHasher is stateless, can instantiate directly or make it a singleton

def get_redis_client_instance(request: Request) -> RedisClient:
    return request.app.state.redis_client # Assuming injected via app.state

# --- JWT Token Verification (unchanged) ---
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthenticatedUser: 
    print(f"DEBUG: verify_token called with credentials: {credentials.credentials[:20]}...")
    
    # Ensure app.state.config is set. This *must* work.
    if not hasattr(app.state, 'config'):
        print("CRITICAL ERROR: app.state.config is NOT set before verify_token is called!")
        raise RuntimeError("app.state.config is not set during verify_token execution.")
    
    config_instance = app.state.config
    print(f"DEBUG: config_instance.JWT_SECRET: {config_instance.JWT_SECRET[:5]}...") # Log part of secret for confirmation

    payload = jwt.decode(
        credentials.credentials, 
        config_instance.JWT_SECRET, 
        algorithms=["HS256"]
    )
    
    print(f"DEBUG: Decoded JWT payload: {json.dumps(payload, indent=2)}")

    user_id = payload.get("sub")
    username = payload.get("username")
    user_roles = payload.get("roles", [])

    print(f"DEBUG: Extracted user_id: {user_id}, username: {username}, roles: {user_roles}")

    if not user_id or not username:
        print(f"DEBUG: Validation failed: Missing 'sub' or 'username'. user_id={user_id}, username={username}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token payload structure.")

    if not isinstance(user_roles, list):
        print(f"DEBUG: Validation failed: Invalid 'roles' type. Type={type(user_roles)}, Value={user_roles}")
        user_roles = [str(user_roles)] if user_roles is not None else []
        # After conversion, re-check type:
        if not isinstance(user_roles, list):
            print(f"DEBUG: Roles conversion failed, still not a list. Final roles: {user_roles}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid 'roles' type after conversion.")


    print(f"DEBUG: Token successfully verified. Returning AuthenticatedUser for {username}.")
    return AuthenticatedUser(
        id=user_id,
        username=username,
        roles=user_roles
    )


# --- API Endpoints ---

@app.get("/status/{device_id}", response_model=Dict[str, Any])
async def get_device_status(device_id: str, 
                            user: AuthenticatedUser = Depends(verify_token), 
                            coap_client: EnhancedCoAPClient = Depends(get_coap_client),
                            redis_client: RedisClient = Depends(get_redis_client_instance)):
     # Try to get from Redis cache first
    cached_data = await redis_client.get(f"latest_sensor_data:{device_id}")
    if cached_data:
        logger.info(f"API: Serving status for {device_id} from Redis cache.")
        return json.loads(cached_data)

    
    #logger.info(f"API: User {user.get('sub')}x requesting status for device {device_id}")
    device_data = await coap_client.get_device_status()
    sensor_data = await coap_client.get_all_sensor_data()

    if not device_data or not sensor_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found or offline.")

    full_data = {**sensor_data, **device_data} # Ensure sensor_data is first for structure
    await redis_client.set(f"latest_sensor_data:{device_id}", json.dumps(full_data), ex=30) # Cache it
    return full_data


@app.post("/control/{device_id}", response_model=Dict[str, Any])
async def send_control_command(device_id: str, 
                               command: ThermostatCommand, 
                               user: Dict = Depends(verify_token), 
                               thermostat_service: ThermostatControlService = Depends(get_thermostat_service)):
    logger.info(f"API: User {user.get('sub')} sending command {command.dict()} to device {device_id}")
    try:
        mock_decision = {
            "action": command.action,
            "target_temperature": command.target_temperature,
            "mode": command.mode or "manual", 
            "fan_speed": command.fan_speed or "auto",
            "reasoning": [f"Manual control via API by user {user.get('sub')}."],
            "confidence": 1.0 
        }
        
        success = await thermostat_service.execute_decision(mock_decision)
        if success:
            return {"status": "success", "command_executed": command.dict(), "device_id": device_id, "timestamp": time.time()}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to execute command on device.")
    except Exception as e:
        logger.error(f"API: Error sending command to {device_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/predictions/{device_id}", response_model=Dict[str, Any])
async def get_temperature_predictions(device_id: str, 
                                      hours: int = 24, 
                                      user: AuthenticatedUser = Depends(verify_token), 
                                      prediction_service: PredictionService = Depends(get_prediction_service)):
    logger.info(f"API: User {user.get('sub')} requesting {hours}-hour predictions for device {device_id}")
    predictions_data = await prediction_service.get_predictions(hours_ahead=hours)
    
    if predictions_data:
        predictions_data["device_id"] = device_id 
        return predictions_data
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Predictions not available.")

@app.get("/maintenance/{device_id}", response_model=Dict[str, Any])
async def get_device_maintenance_status(device_id: str, 
                                        user: AuthenticatedUser = Depends(verify_token), 
                                        maintenance_service: MaintenanceService = Depends(get_maintenance_service),
                                        coap_client: EnhancedCoAPClient = Depends(get_coap_client)):
    logger.info(f"API: User {user.get('sub')} requesting maintenance status for device {device_id}")
    device_status_full = await coap_client.get_device_status()
    if not device_status_full:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} status not available for maintenance check.")
    
    maintenance_info = await maintenance_service.check_maintenance_needs(device_status_full)
    
    if maintenance_info:
        return maintenance_info
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance information not available for this device.")

@app.get("/energy/{device_id}", response_model=Dict[str, Any])
async def get_energy_data(device_id: str, 
                          days: int = 7, 
                          user: AuthenticatedUser = Depends(verify_token), 
                          influx_client: InfluxDBClient = Depends(get_influxdb_client)):
    logger.info(f"API: User {user.get('sub')} requesting {days}-day energy data for device {device_id}")
    energy_data_list = await influx_client.get_energy_data(device_id, days=days)

    if not energy_data_list:
        return {
            "daily_data": [],
            "total_consumption_kwh": 0.0,
            "average_daily_kwh": 0.0,
            "cost_projection_monthly_usd": 0.0,
            "device_id": device_id,
            "message": "No energy data available for this period."
        }
    
    processed_daily_data = []
    total_consumption_kwh = 0.0
    for entry in energy_data_list:
        processed_daily_data.append({
            "timestamp": entry['time'],
            "consumption_kwh": round(entry['value'], 2)
        })
        total_consumption_kwh += entry['value']

    average_daily_kwh = total_consumption_kwh / days if days > 0 else 0.0
    cost_projection_monthly_usd = average_daily_kwh * 30 * 0.15 
    
    return {
        "daily_data": processed_daily_data, 
        "total_consumption_kwh": round(total_consumption_kwh, 2),
        "average_daily_kwh": round(average_daily_kwh, 2),
        "cost_projection_monthly_usd": round(cost_projection_monthly_usd, 2),
        "device_id": device_id
    }

# --- NEW: Authentication Endpoint (for mobile-api to call) ---
@app.post("/auth/login", response_model=Dict[str, str])
async def authenticate_user(login_data: LoginRequest, 
                           db: Session = Depends(get_postgres_db_session), # <--- Use PostgreSQL session
                           password_hasher: PasswordHasher = Depends(get_password_hasher)): # <--- Use PasswordHasher
    """
    Authenticates user credentials against the PostgreSQL database and issues a JWT.
    This endpoint is intended to be called by the mobile-api service.
    """
    # Fetch user from PostgreSQL
    user = db.query(User).filter(User.username == login_data.username).first()
  
    if not user:
        logger.warning(f"Authentication failed: User '{login_data.username}' not found.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Verify password
    if not password_hasher.verify_password(login_data.password, user.password_hash):
        logger.warning(f"Authentication failed for user '{login_data.username}': Invalid password.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Generate JWT Token
    jwt_secret = app.state.config.JWT_SECRET 
    

    token_payload = {
        "sub": str(user.id), # Ensure UUID is converted to string for JWT payload
        "username": user.username,
        "roles": user.roles if user.roles is not None else [], 
        "exp": datetime.now(timezone.utc) + timedelta(hours=24), 
        
        "iat": datetime.now(timezone.utc) # Add "issued at" timestamp for JWT best practice
    }
    jwt_token = jwt.encode(token_payload, jwt_secret, algorithm="HS256")
    logger.info(f"User '{user.username}' authenticated successfully. Issued JWT.")
    
    # Optional: Update last_login_at in DB
    user.last_login_at = datetime.now(timezone.utc)

    db.commit() # Commit changes to DB
    db.refresh(user) # Refresh user object to get latest state

    return {"access_token": jwt_token, "token_type": "bearer"}



# Inside register_user function:
@app.post("/auth/register", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def register_user(reg_data: RegisterRequest, 
                       db: Session = Depends(get_postgres_db_session), 
                       password_hasher: PasswordHasher = Depends(get_password_hasher)):
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == reg_data.username).first() 
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")
    # Hash the password
    hashed_password = password_hasher.hash_password(reg_data.password)


    new_user = User(
        username=reg_data.username, 
        email=reg_data.email, 
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user) 

    logger.info(f"User '{reg_data.username}' registered successfully with ID: {new_user.id}")
    return {"message": "User registered successfully."}

@app.get("/metrics")
async def metrics():
    """
    Endpoint for Prometheus to scrape metrics.
    """
    return Response(generate_latest(), media_type="text/plain")

# Add these routes to your main FastAPI app file (where you have your other routes)
# This should go in your api/rest_gateway.py or wherever your main FastAPI routes are defined


# Enhanced FCM routes with validation and better error handling
# Add these to your main FastAPI app



# Enhanced Pydantic models
class FCMTokenRequest(BaseModel):
    token: str
    platform: str = "web"
    userAgent: str = ""
    timestamp: str = ""
    userId: str = ""
    username: str = "Anonymous"
    email: str = ""
    validate_immediately: bool = False  # Option to validate token immediately

class FCMUnregisterRequest(BaseModel):
    token: str
    userId: str = ""
    timestamp: str = ""

class TestNotificationRequest(BaseModel):
    title: str = "Test Notification"
    body: str = "This is a test notification"
    validate_tokens: bool = True  # Validate tokens before sending

class TokenValidationRequest(BaseModel):
    tokens: Optional[List[str]] = None  # If None, validate all tokens
    force: bool = False

# Enhanced FCM Routes
@app.post("/register")
async def register_fcm_token(request: FCMTokenRequest):
    """Register FCM token with enhanced validation"""
    try:
        logger.info(f"FCM token registration request: User={request.username} ({request.userId}), Token={request.token[:20]}...")
        
        # Get notification service from app state
        notification_service = app.state.notification_service
        
        # Prepare user info
        user_info = {
            "username": request.username,
            "userId": request.userId,
            "email": request.email,
            "platform": request.platform,
            "userAgent": request.userAgent,
            "registeredAt": request.timestamp or datetime.now().isoformat()
        }
        
        # Add token with metadata
        is_new = await notification_service.fcm_token_manager.add_token(request.token, user_info)
        
        # Optionally validate immediately
        validation_result = None
        if request.validate_immediately:
            try:
                is_valid, error_msg = await notification_service.fcm_token_manager.validator.validate_token(request.token)
                validation_result = {
                    "is_valid": is_valid,
                    "error": error_msg if not is_valid else None
                }
                if not is_valid:
                    logger.warning(f"Newly registered token failed validation: {request.token[:20]}... - {error_msg}")
            except Exception as e:
                logger.error(f"Error validating newly registered token: {e}")
                validation_result = {"is_valid": False, "error": f"Validation error: {str(e)}"}
        
        # Get current statistics
        stats = await notification_service.fcm_token_manager.get_statistics()
        
        response = {
            "success": True,
            "message": f"Token {'registered' if is_new else 'updated'} successfully for {request.username}",
            "userId": request.userId,
            "isNew": is_new,
            "statistics": stats
        }
        
        if validation_result:
            response["validation"] = validation_result
        
        logger.info(f"✅ FCM token {'registered' if is_new else 'updated'} for {request.username}")
        return response
            
    except Exception as e:
        logger.error(f"❌ Error registering FCM token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register token: {str(e)}")

@app.post("/unregister")
async def unregister_fcm_token(request: FCMUnregisterRequest):
    """Unregister FCM token"""
    try:
        logger.info(f"FCM token unregistration request: User={request.userId}, Token={request.token[:20]}...")
        
        # Get notification service from app state
        notification_service = app.state.notification_service
        
        # Remove token
        success = await notification_service.fcm_token_manager.remove_token(request.token)
        
        # Get current statistics
        stats = await notification_service.fcm_token_manager.get_statistics()
        
        return {
            "success": True,
            "message": "Token unregistered successfully" if success else "Token not found (may have been already removed)",
            "removed": success,
            "statistics": stats
        }
            
    except Exception as e:
        logger.error(f"❌ Error unregistering FCM token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to unregister token: {str(e)}")

@app.get("/fcm/health")
async def fcm_health_check():
    """Enhanced health check for FCM service"""
    try:
        notification_service = app.state.notification_service
        
        # Get token statistics
        stats = await notification_service.fcm_token_manager.get_statistics()
        token_info = await notification_service.fcm_token_manager.get_token_info()
        
        # Check Firebase status
        firebase_initialized = False
        try:
            import firebase_admin
            firebase_initialized = len(firebase_admin._apps) > 0
        except ImportError:
            pass
        
        return {
            "status": "FCM service running",
            "timestamp": datetime.now().isoformat(),
            "firebase_initialized": firebase_initialized,
            "statistics": stats,
            "last_validation": notification_service.fcm_token_manager.last_validation.isoformat() if notification_service.fcm_token_manager.last_validation else None
        }
    except Exception as e:
        logger.error(f"FCM health check failed: {e}")
        raise HTTPException(status_code=500, detail="FCM service unavailable")

@app.post("/fcm/validate-tokens")
async def validate_tokens(request: TokenValidationRequest):
    """Validate FCM tokens on demand"""
    try:
        notification_service = app.state.notification_service
        
        if request.tokens:
            # Validate specific tokens
            logger.info(f"Validating {len(request.tokens)} specific FCM tokens...")
            validation_results = await notification_service.fcm_token_manager.validator.validate_tokens_batch(request.tokens)
            
            valid_count = sum(1 for is_valid, _ in validation_results.values() if is_valid)
            invalid_count = len(validation_results) - valid_count
            
            return {
                "success": True,
                "message": f"Validated {len(request.tokens)} tokens",
                "results": {
                    token[:20] + "...": {"valid": is_valid, "error": error_msg if not is_valid else None}
                    for token, (is_valid, error_msg) in validation_results.items()
                },
                "summary": {
                    "total": len(validation_results),
                    "valid": valid_count,
                    "invalid": invalid_count
                }
            }
        else:
            # Validate all tokens
            logger.info("Validating all FCM tokens...")
            await notification_service.fcm_token_manager.validate_all_tokens(force=request.force)
            
            stats = await notification_service.fcm_token_manager.get_statistics()
            
            return {
                "success": True,
                "message": "All tokens validated",
                "statistics": stats
            }
            
    except Exception as e:
        logger.error(f"Error validating FCM tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate tokens: {str(e)}")

@app.post("/fcm/test-notification")
async def send_test_fcm_notification(request: TestNotificationRequest):
    """Send a test FCM notification with enhanced error handling"""
    try:
        logger.info(f"Sending test FCM notification: {request.title}")
        
        # Get notification service from app state
        notification_service = app.state.notification_service
        
        # Optionally validate tokens before sending
        if request.validate_tokens:
            logger.info("Validating tokens before sending test notification...")
            await notification_service.fcm_token_manager.validate_all_tokens(force=True)
        
        # Get valid tokens
        tokens = await notification_service.fcm_token_manager.get_valid_tokens()
        
        if not tokens:
            return {
                "success": False,
                "message": "No valid FCM tokens available",
                "details": "Register some tokens first or check token validity"
            }
        
        # Send test alert through notification service
        await notification_service.send_alert(
            alert_type="test_notification",
            message=request.body,
            data={"title": request.title, "test": True, "timestamp": datetime.now().isoformat()}
        )
        
        # Get updated statistics
        stats = await notification_service.fcm_token_manager.get_statistics()
        
        return {
            "success": True,
            "message": f"Test notification sent to {len(tokens)} registered devices",
            "title": request.title,
            "body": request.body,
            "target_tokens": len(tokens),
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Error sending test FCM notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")

@app.get("/fcm/tokens")
async def get_registered_tokens(
    include_details: bool = Query(False, description="Include detailed token information"),
    status_filter: Optional[str] = Query(None, description="Filter by status: active, invalid")
):
    """Get list of registered FCM tokens with optional filtering"""
    try:
        notification_service = app.state.notification_service
        
        if include_details:
            token_info = await notification_service.fcm_token_manager.get_token_info()
            
            # Apply status filter if provided
            if status_filter:
                if status_filter == "active":
                    token_info = [t for t in token_info if t["is_valid"]]
                elif status_filter == "invalid":
                    token_info = [t for t in token_info if not t["is_valid"]]
            
            return {
                "success": True,
                "tokens": token_info,
                "statistics": await notification_service.fcm_token_manager.get_statistics()
            }
        else:
            # Simple token list
            if status_filter == "active":
                tokens = await notification_service.fcm_token_manager.get_valid_tokens()
            else:
                tokens = [t["token"] for t in notification_service.fcm_token_manager.tokens]
                if status_filter == "invalid":
                    valid_tokens = await notification_service.fcm_token_manager.get_valid_tokens()
                    tokens = [t for t in tokens if t not in valid_tokens]
            
            # Only return partial tokens for security
            partial_tokens = [f"{token[:20]}..." for token in tokens]
            
            return {
                "success": True,
                "token_count": len(tokens),
                "tokens": partial_tokens,
                "statistics": await notification_service.fcm_token_manager.get_statistics()
            }
    except Exception as e:
        logger.error(f"Error getting FCM tokens: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tokens")

@app.post("/fcm/cleanup")
async def cleanup_tokens(max_age_days: int = Query(30, description="Maximum age in days for tokens to keep")):
    """Clean up old and invalid FCM tokens"""
    try:
        notification_service = app.state.notification_service
        
        # Get stats before cleanup
        stats_before = await notification_service.fcm_token_manager.get_statistics()
        
        # Perform cleanup
        await notification_service.fcm_token_manager.cleanup_old_tokens(max_age_days)
        
        # Get stats after cleanup
        stats_after = await notification_service.fcm_token_manager.get_statistics()
        
        removed_count = stats_before["total"] - stats_after["total"]
        
        return {
            "success": True,
            "message": f"Cleanup completed. Removed {removed_count} old tokens",
            "removed_count": removed_count,
            "statistics_before": stats_before,
            "statistics_after": stats_after
        }
        
    except Exception as e:
        logger.error(f"Error during token cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup tokens: {str(e)}")

@app.post("/alert/test")
async def send_test_alert(
    alert_type: str = Query("test_notification", description="Type of alert to send"),
    message: str = Query("Test alert message", description="Alert message"),
    validate_tokens: bool = Query(True, description="Validate tokens before sending")
):
    """Send a test alert through all notification channels"""
    try:
        notification_service = app.state.notification_service
        
        # Optionally validate tokens before sending
        if validate_tokens:
            await notification_service.fcm_token_manager.validate_all_tokens(force=True)
        
        # Send the alert
        await notification_service.send_alert(
            alert_type=alert_type,
            message=message,
            data={"test": True, "manual_trigger": True, "timestamp": datetime.now().isoformat()}
        )
        
        # Get token statistics
        stats = await notification_service.fcm_token_manager.get_statistics()
        
        return {
            "success": True,
            "message": f"Test alert '{alert_type}' sent successfully",
            "alert_type": alert_type,
            "alert_message": message,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error sending test alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test alert: {str(e)}")