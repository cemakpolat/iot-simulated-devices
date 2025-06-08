# # mobile/api/mobile_endpoints.py
# from fastapi import FastAPI, HTTPException, Depends
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from pydantic import BaseModel
# from typing import List, Optional
# import jwt

# app = FastAPI(title="Smart Thermostat Mobile API", version="2.0.0")
# security = HTTPBearer()

# class ThermostatCommand(BaseModel):
#     action: str
#     target_temperature: Optional[float] = None
#     mode: Optional[str] = None
#     fan_speed: Optional[str] = None

# class ScheduleEntry(BaseModel):
#     time: str
#     temperature: float
#     days: List[str]
#     enabled: bool = True

# class UserPreferences(BaseModel):
#     comfort_temperature: float = 22.0
#     energy_saving_mode: bool = False
#     notifications_enabled: bool = True
#     auto_mode_enabled: bool = True

# def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     """Verify JWT token"""
#     try:
#         payload = jwt.decode(
#             credentials.credentials, 
#             os.getenv("JWT_SECRET", "secret"), 
#             algorithms=["HS256"]
#         )
#         return payload
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")

# @app.get("/api/v1/status")
# async def get_device_status(user=Depends(verify_token)):
#     """Get current device status"""
#     # In real implementation, fetch from CoAP device
#     return {
#         "device_id": "smart-thermostat-01",
#         "online": True,
#         "current_temperature": 23.5,
#         "target_temperature": 22.0,
#         "humidity": 45.2,
#         "air_quality": {"aqi": 35, "quality": "good"},
#         "hvac_state": "cooling",
#         "energy_consumption": 2.1,
#         "last_updated": time.time()
#     }

# @app.post("/api/v1/control")
# async def send_command(command: ThermostatCommand, user=Depends(verify_token)):
#     """Send control command to thermostat"""
#     try:
#         # In real implementation, send to CoAP device
#         result = {
#             "success": True,
#             "command_executed": command.dict(),
#             "timestamp": time.time()
#         }
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/api/v1/predictions")
# async def get_predictions(hours: int = 6, user=Depends(verify_token)):
#     """Get temperature predictions"""
#     # Mock predictions
#     predictions = []
#     for i in range(hours):
#         predictions.append({
#             "hour": i + 1,
#             "temperature": round(22 + random.uniform(-1, 1), 1),
#             "confidence": round(random.uniform(0.8, 0.95), 2)
#         })
    
#     return {
#         "predictions": predictions,
#         "model_accuracy": 0.89,
#         "last_updated": time.time()
#     }

# @app.get("/api/v1/energy")
# async def get_energy_data(days: int = 7, user=Depends(verify_token)):
#     """Get energy consumption data"""
#     energy_data = []
#     for i in range(days):
#         energy_data.append({
#             "date": (datetime.now() - timedelta(days=i)).isoformat(),
#             "consumption": round(random.uniform(15, 35), 2),
#             "cost": round(random.uniform(1.8, 4.2), 2),
#             "efficiency_score": round(random.uniform(0.7, 0.95), 2)
#         })
    
#     return {
#         "daily_data": energy_data,
#         "total_consumption": sum(d["consumption"] for d in energy_data),
#         "average_daily": sum(d["consumption"] for d in energy_data) / len(energy_data),
#         "cost_projection": round(random.uniform(45, 85), 2)
#     }

# @app.post("/api/v1/schedule")
# async def set_schedule(schedule: List[ScheduleEntry], user=Depends(verify_token)):
#     """Set thermostat schedule"""
#     # In real implementation, store in database
#     return {
#         "success": True,
#         "schedule_entries": len(schedule),
#         "message": "Schedule updated successfully"
#     }

# @app.get("/api/v1/maintenance")
# async def get_maintenance_status(user=Depends(verify_token)):
#     """Get maintenance recommendations"""
#     return {
#         "maintenance_score": 25,
#         "priority": "low",
#         "last_service": "2024-01-15",
#         "next_recommended": "2024-07-15",
#         "recommendations": [
#             "Clean air filter",
#             "Check refrigerant levels"
#         ],
#         "estimated_cost": 120.00
#     }

# # Push notification service
# from mobile.push_notifications import PushNotificationService

# push_service = PushNotificationService()

# @app.post("/api/v1/register-device")
# async def register_mobile_device(device_data: dict, user=Depends(verify_token)):
#     """Register mobile device for push notifications"""
#     device_token = device_data.get("device_token")
#     platform = device_data.get("platform")  # ios/android
    
#     success = await push_service.register_device(
#         user_id=user["user_id"],
#         device_token=device_token,
#         platform=platform
#     )
    
#     return {"success": success}


# mobile/api/mobile_endpoints.py
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import jwt
import os
import time
import random # For mock data
from datetime import datetime, timedelta
import logging

# Import PushNotificationService
from push_notifications import PushNotificationService

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Smart Thermostat Mobile API", version="2.0.0")

# Security schema for JWT
security = HTTPBearer()

# --- Initialize Push Notification Service ---
# This instance will be created once when the API starts.
push_service = PushNotificationService()

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

class DeviceRegistration(BaseModel):
    device_token: str # FCM token for push notifications
    platform: str # "ios" or "android"
    # Additional fields like app_version, device_model etc.

# --- JWT Token Verification ---
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifies the JWT token from the Authorization header."""
    try:
        # Load JWT_SECRET from environment. In a real app, use a proper config loader.
        jwt_secret = os.getenv("JWT_SECRET", "your-secret-key")
        if jwt_secret == "your-secret-key":
            logger.warning("JWT_SECRET is using default value in mobile API. Please set it securely in .env.")

        payload = jwt.decode(
            credentials.credentials, 
            jwt_secret, 
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Mobile API: JWT token expired.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        logger.warning("Mobile API: Invalid JWT token received.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception as e:
        logger.error(f"Mobile API: Unexpected error during token verification: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token verification error.")

# --- API Endpoints ---

@app.get("/status/{device_id}", response_model=Dict[str, Any])
async def get_device_status(device_id: str, user: Dict = Depends(verify_token)):
    """
    Retrieves the current status and sensor data of a specific thermostat device.
    In a full system, this would call the AI Controller's REST API endpoint.
    For this phase, it returns mock data.
    """
    logger.info(f"Mobile API: User {user.get('sub')} requesting status for device {device_id}")
    return {
        "device_id": device_id,
        "online": True,
        "current_temperature": round(20 + random.uniform(-2, 5), 1),
        "target_temperature": 22.0,
        "humidity": round(40 + random.uniform(-5, 10), 1),
        "air_quality": {"aqi": random.randint(20, 150), "quality": "good" if random.randint(0,100) < 70 else "moderate"},
        "hvac_state": random.choice(["cooling", "heating", "off"]),
        "energy_consumption": round(random.uniform(1.0, 3.5), 2),
        "last_updated": time.time()
    }

@app.post("/control/{device_id}", response_model=Dict[str, Any])
async def send_control_command(device_id: str, command: ThermostatCommand, user: Dict = Depends(verify_token)):
    """
    Sends a control command to the thermostat device.
    In a full system, this would forward the command to the AI Controller's REST API.
    For this phase, it returns a mock success.
    """
    logger.info(f"Mobile API: User {user.get('sub')} sending command {command.dict()} to device {device_id}")
    try:
        # Simulate sending command to AI Controller and getting response
        # In actual implementation:
        # ai_controller_response = await aiohttp_client.post(f"http://ai-controller:8000/api/v1/control/{device_id}", json=command.dict())
        # ai_controller_response.raise_for_status()
        # result = await ai_controller_response.json()
        
        result = {
            "success": True,
            "command_executed": command.dict(),
            "device_id": device_id,
            "timestamp": time.time()
        }
        return result
    except Exception as e:
        logger.error(f"Mobile API: Error sending command to {device_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/predictions/{device_id}", response_model=Dict[str, Any])
async def get_temperature_predictions(device_id: str, hours: int = 6, user: Dict = Depends(verify_token)):
    """
    Retrieves temperature predictions for the next few hours for a specific device.
    In a full system, this would call the AI Controller's REST API.
    For this phase, it returns mock data.
    """
    logger.info(f"Mobile API: User {user.get('sub')} requesting {hours}-hour predictions for device {device_id}")
    predictions = []
    current_temp = round(20 + random.uniform(-2, 5), 1)
    for i in range(hours):
        predictions.append({
            "hour_ahead": i + 1,
            "temperature": round(current_temp + random.uniform(-1, 1), 1),
            "confidence": round(random.uniform(0.8, 0.95), 2)
        })
    
    return {
        "predictions": predictions,
        "model_accuracy": 0.89,
        "last_updated": time.time(),
        "device_id": device_id
    }

@app.get("/energy/{device_id}", response_model=Dict[str, Any])
async def get_energy_data(device_id: str, days: int = 7, user: Dict = Depends(verify_token)):
    """
    Retrieves historical energy consumption data for a specific device.
    In a full system, this would call the AI Controller's REST API.
    For this phase, it returns mock data.
    """
    logger.info(f"Mobile API: User {user.get('sub')} requesting {days}-day energy data for device {device_id}")
    energy_data = []
    for i in range(days):
        energy_data.append({
            "date": (datetime.now() - timedelta(days=i)).isoformat().split('T')[0],
            "consumption_kwh": round(random.uniform(15, 35), 2),
            "cost_usd": round(random.uniform(1.8, 4.2), 2),
            "efficiency_score": round(random.uniform(0.7, 0.95), 2)
        })
    
    total_consumption = sum(d["consumption_kwh"] for d in energy_data)
    average_daily = total_consumption / len(energy_data) if energy_data else 0

    return {
        "daily_data": energy_data,
        "total_consumption_kwh": round(total_consumption, 2),
        "average_daily_kwh": round(average_daily, 2),
        "cost_projection_monthly_usd": round(average_daily * 30 * 0.15, 2), 
        "device_id": device_id
    }

@app.post("/schedule/{device_id}", response_model=Dict[str, Any])
async def set_schedule(device_id: str, schedule: List[ScheduleEntry], user: Dict = Depends(verify_token)):
    """
    Sets thermostat schedule.
    In a full system, this would update the schedule in PostgreSQL and potentially send it to the device.
    For this phase, it returns a mock success.
    """
    logger.info(f"Mobile API: User {user.get('sub')} setting schedule for device {device_id} with {len(schedule)} entries.")
    return {
        "success": True,
        "schedule_entries_count": len(schedule),
        "message": "Schedule updated successfully (mock)",
        "device_id": device_id
    }

@app.get("/maintenance/{device_id}", response_model=Dict[str, Any])
async def get_maintenance_status(device_id: str, user: Dict = Depends(verify_token)):
    """
    Retrieves predictive maintenance recommendations and status for a specific device.
    In a full system, this would call the AI Controller's REST API.
    For this phase, it returns mock data.
    """
    logger.info(f"Mobile API: User {user.get('sub')} requesting maintenance status for device {device_id}")
    return {
        "device_id": device_id,
        "maintenance_score": random.randint(10, 80),
        "priority": random.choice(["low", "medium", "high", "critical"]),
        "last_service": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat().split('T')[0],
        "next_recommended": (datetime.now() + timedelta(days=random.randint(30, 180))).isoformat().split('T')[0],
        "recommendations": [
            "Clean air filter",
            "Check refrigerant levels",
            "Inspect outdoor unit",
            "Calibrate temperature sensor"
        ],
        "estimated_cost_usd": round(random.uniform(100, 500), 2)
    }

@app.post("/register-device", response_model=Dict[str, Any])
async def register_mobile_device(device_data: DeviceRegistration, user: Dict = Depends(verify_token)):
    """
    Registers a mobile device for push notifications.
    Stores the device token (FCM/APN) associated with a user.
    """
    user_id = user.get("sub") # Assuming 'sub' is the user_id from JWT payload
    device_token = device_data.device_token
    platform = device_data.platform  # "ios" or "android"
    
    logger.info(f"Mobile API: User {user_id} registering device token: {device_token[:10]}... on platform: {platform}")
    success = await push_service.register_device(
        user_id=user_id,
        device_token=device_token,
        platform=platform
    )
    
    return {"success": success, "message": "Device registration status."}

@app.post("/send-push-test/{user_id}", response_model=Dict[str, Any])
async def send_test_push_notification(user_id: str, user: Dict = Depends(verify_token)):
    """
    Sends a test push notification to a specific user's registered devices.
    (Requires proper Firebase setup for `push_notifications.py` to work)
    """
    current_user_id = user.get("sub")
    if current_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot send test notification for another user.")

    logger.info(f"Mobile API: User {user_id} requesting test push notification.")
    success = await push_service.send_notification(
        user_id=user_id,
        title="Thermostat Test Alert 🔔",
        body="This is a test notification from your Smart Thermostat System! Check your app.",
        data={"alert_type": "test_notification", "source": "mobile_api_test"}
    )
    return {"success": success, "message": "Test notification sent status."}

# Placeholder for user login/token generation
@app.post("/login", response_model=Dict[str, str])
async def login(username: str, password: str):
    """
    Simulates a user login and generates a JWT token.
    In a real app, this would verify credentials against a database.
    """
    # Dummy credentials for demonstration
    if username == "testuser" and password == "testpass":
        config = ServerConfig()
        token_payload = {
            "sub": "testuser_id_123", # Subject (user ID)
            "username": "testuser",
            "exp": datetime.utcnow() + timedelta(hours=24) # Token expires in 24 hours
        }
        token = jwt.encode(token_payload, config.JWT_SECRET, algorithm="HS256")
        logger.info(f"Generated JWT token for user: {username}")
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")