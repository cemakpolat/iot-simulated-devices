# mobile/api/mobile_endpoints.py
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form, Header # <--- Ensure Header is here
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import jwt
import os 
import time
import random 
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp 

from ..push_notifications import PushNotificationService

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Smart Thermostat Mobile API", version="2.0.0")

# Security schema for JWT
security = HTTPBearer()

# Initialize Push Notification Service
push_service = PushNotificationService()

# --- Base URL for AI Controller API ---
AI_CONTROLLER_API_BASE_URL = os.getenv("AI_CONTROLLER_API_URL", "http://ai-controller:8000")
logger.info(f"Mobile API configured to connect to AI Controller at: {AI_CONTROLLER_API_BASE_URL}")

# Pydantic models for request/response bodies (unchanged)
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
    device_token: str 
    platform: str 

# --- JWT Token Verification (unchanged) ---
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
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

# --- API Endpoints: NOW PROXYING TO AI CONTROLLER WITH TOKEN FORWARDING ---

@app.get("/status/{device_id}", response_model=Dict[str, Any])
async def get_device_status(device_id: str, 
                            user: Dict = Depends(verify_token), # Original token validation
                            authorization: Optional[str] = Header(None) # <--- ADDED to signature
                           ):
    """
    Retrieves the current status and sensor data of a specific thermostat device from AI Controller.
    """
    logger.info(f"Mobile API: User {user.get('sub')} requesting status for device {device_id} from AI Controller.")
    
    headers = {}
    if authorization:
        headers["Authorization"] = authorization # <--- Forward the token

    try:
        async with aiohttp.ClientSession(headers=headers) as session: # <--- PASS HEADERS HERE
            async with session.get(f"{AI_CONTROLLER_API_BASE_URL}/status/{device_id}", timeout=10) as resp:
                resp.raise_for_status() 
                return await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"Mobile API: Error fetching status for {device_id} from AI Controller: {e}", exc_info=True)
        if isinstance(e, aiohttp.ClientResponseError):
            raise HTTPException(status_code=e.status, detail=f"AI Controller error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch device status: {e}")
    except asyncio.TimeoutError:
        logger.error(f"Mobile API: Timeout fetching status for {device_id} from AI Controller.")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="AI Controller response timed out.")
    except Exception as e:
        logger.error(f"Mobile API: Unexpected error in get_device_status: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@app.post("/control/{device_id}", response_model=Dict[str, Any])
async def send_control_command(device_id: str, 
                               command: ThermostatCommand, 
                               user: Dict = Depends(verify_token),
                               authorization: Optional[str] = Header(None) # <--- ADDED to signature
                              ):
    """
    Sends a control command to the thermostat device via the AI Controller.
    """
    logger.info(f"Mobile API: User {user.get('sub')} sending command {command.dict()} to device {device_id} via AI Controller.")
    
    headers = {}
    if authorization:
        headers["Authorization"] = authorization # <--- Forward the token

    try:
        async with aiohttp.ClientSession(headers=headers) as session: # <--- PASS HEADERS HERE
            async with session.post(f"{AI_CONTROLLER_API_BASE_URL}/control/{device_id}", json=command.dict(), timeout=10) as resp:
                resp.raise_for_status() 
                return await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"Mobile API: Error sending control command for {device_id} to AI Controller: {e}", exc_info=True)
        if isinstance(e, aiohttp.ClientResponseError):
            raise HTTPException(status_code=e.status, detail=f"AI Controller error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send control command: {e}")
    except asyncio.TimeoutError:
        logger.error(f"Mobile API: Timeout sending control command for {device_id} to AI Controller.")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="AI Controller response timed out.")
    except Exception as e:
        logger.error(f"Mobile API: Unexpected error in send_control_command: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@app.get("/predictions/{device_id}", response_model=Dict[str, Any])
async def get_temperature_predictions(device_id: str, 
                                      hours: int = 6, 
                                      user: Dict = Depends(verify_token),
                                      authorization: Optional[str] = Header(None) # <--- ADDED to signature
                                     ):
    """
    Retrieves temperature predictions for the next few hours for a specific device from AI Controller.
    """
    logger.info(f"Mobile API: User {user.get('sub')} requesting {hours}-hour predictions for device {device_id} from AI Controller.")
    
    headers = {}
    if authorization:
        headers["Authorization"] = authorization

    try:
        async with aiohttp.ClientSession(headers=headers) as session: # <--- PASS HEADERS HERE
            async with session.get(f"{AI_CONTROLLER_API_BASE_URL}/predictions/{device_id}?hours={hours}", timeout=10) as resp:
                resp.raise_for_status() 
                return await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"Mobile API: Error fetching predictions for {device_id} from AI Controller: {e}", exc_info=True)
        if isinstance(e, aiohttp.ClientResponseError):
            raise HTTPException(status_code=e.status, detail=f"AI Controller error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch predictions: {e}")
    except asyncio.TimeoutError:
        logger.error(f"Mobile API: Timeout fetching predictions for {device_id} from AI Controller.")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="AI Controller response timed out.")
    except Exception as e:
        logger.error(f"Mobile API: Unexpected error in get_temperature_predictions: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.get("/energy/{device_id}", response_model=Dict[str, Any])
async def get_energy_data(device_id: str, 
                          days: int = 7, 
                          user: Dict = Depends(verify_token),
                          authorization: Optional[str] = Header(None) # <--- ADDED to signature
                         ):
    """
    Retrieves historical energy consumption data for a specific device from AI Controller.
    """
    logger.info(f"Mobile API: User {user.get('sub')} requesting {days}-day energy data for device {device_id} from AI Controller.")
    
    headers = {}
    if authorization:
        headers["Authorization"] = authorization

    try:
        async with aiohttp.ClientSession(headers=headers) as session: # <--- PASS HEADERS HERE
            async with session.get(f"{AI_CONTROLLER_API_BASE_URL}/energy/{device_id}?days={days}", timeout=10) as resp:
                resp.raise_for_status() 
                return await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"Mobile API: Error fetching energy data for {device_id} from AI Controller: {e}", exc_info=True)
        if isinstance(e, aiohttp.ClientResponseError):
            raise HTTPException(status_code=e.status, detail=f"AI Controller error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch energy data: {e}")
    except asyncio.TimeoutError:
        logger.error(f"Mobile API: Timeout fetching energy data for {device_id} from AI Controller.")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="AI Controller response timed out.")
    except Exception as e:
        logger.error(f"Mobile API: Unexpected error in get_energy_data: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.post("/schedule/{device_id}", response_model=Dict[str, Any])
async def set_schedule(device_id: str, 
                       schedule: List[ScheduleEntry], 
                       user: Dict = Depends(verify_token),
                       authorization: Optional[str] = Header(None) # <--- ADDED to signature
                      ):
    """
    Sets thermostat schedule via the AI Controller.
    """
    logger.info(f"Mobile API: User {user.get('sub')} setting schedule for device {device_id} with {len(schedule)} entries via AI Controller.")
    
    headers = {}
    if authorization:
        headers["Authorization"] = authorization

    try:
        async with aiohttp.ClientSession(headers=headers) as session: # <--- PASS HEADERS HERE
            async with session.post(f"{AI_CONTROLLER_API_BASE_URL}/schedule/{device_id}", json=[s.dict() for s in schedule], timeout=10) as resp:
                resp.raise_for_status() 
                return await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"Mobile API: Error setting schedule for {device_id} via AI Controller: {e}", exc_info=True)
        if isinstance(e, aiohttp.ClientResponseError):
            raise HTTPException(status_code=e.status, detail=f"AI Controller error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to set schedule: {e}")
    except asyncio.TimeoutError:
        logger.error(f"Mobile API: Timeout setting schedule for {device_id} via AI Controller.")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="AI Controller response timed out.")
    except Exception as e:
        logger.error(f"Mobile API: Unexpected error in set_schedule: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.get("/maintenance/{device_id}", response_model=Dict[str, Any])
async def get_maintenance_status(device_id: str, 
                                 user: Dict = Depends(verify_token),
                                 authorization: Optional[str] = Header(None) # <--- ADDED to signature
                                ):
    """
    Retrieves predictive maintenance recommendations and status for a specific device from AI Controller.
    """
    logger.info(f"Mobile API: User {user.get('sub')} requesting maintenance status for device {device_id} from AI Controller.")
    
    headers = {}
    if authorization:
        headers["Authorization"] = authorization

    try:
        async with aiohttp.ClientSession(headers=headers) as session: # <--- PASS HEADERS HERE
            async with session.get(f"{AI_CONTROLLER_API_BASE_URL}/maintenance/{device_id}", timeout=10) as resp:
                resp.raise_for_status() 
                return await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"Mobile API: Error fetching maintenance status for {device_id} from AI Controller: {e}", exc_info=True)
        if isinstance(e, aiohttp.ClientResponseError):
            raise HTTPException(status_code=e.status, detail=f"AI Controller error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch maintenance status: {e}")
    except asyncio.TimeoutError:
        logger.error(f"Mobile API: Timeout fetching maintenance status for {device_id} from AI Controller.")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="AI Controller response timed out.")
    except Exception as e:
        logger.error(f"Mobile API: Unexpected error in get_maintenance_status: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.post("/register-device", response_model=Dict[str, Any])
async def register_mobile_device(device_data: DeviceRegistration, 
                                 user: Dict = Depends(verify_token),
                                 authorization: Optional[str] = Header(None) # <--- ADDED to signature (even if not always needed)
                                ):
    """
    Registers a mobile device for push notifications.
    Stores the device token (FCM/APN) associated with a user.
    """
    user_id = user.get("sub") 
    device_token = device_data.device_token
    platform = device_data.platform  
    
    logger.info(f"Mobile API: User {user_id} registering device token: {device_token[:10]}... on platform: {platform}")
    success = await push_service.register_device(
        user_id=user_id,
        device_token=device_token,
        platform=platform
    )
    
    return {"success": success, "message": "Device registration status."}

@app.post("/send-push-test/{user_id_param}", response_model=Dict[str, Any])
async def send_test_push_notification(user_id_param: str, 
                                      user: Dict = Depends(verify_token),
                                      authorization: Optional[str] = Header(None) # <--- ADDED to signature (even if not always needed)
                                     ):
    """
    Sends a test push notification to a specific user's registered devices.
    """
    current_user_id = user.get("sub")
    if current_user_id != user_id_param: 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot send test notification for another user.")

    logger.info(f"Mobile API: User {user_id_param} requesting test push notification.")
    success = await push_service.send_notification(
        user_id=user_id_param, # Use path parameter as recipient ID
        title="Thermostat Test Alert 🔔",
        body="This is a test notification from your Smart Thermostat System! Check your app.",
        data={"alert_type": "test_notification", "source": "mobile_api_test"}
    )
    return {"success": success, "message": "Test notification sent status."}


@app.post("/login", response_model=Dict[str, str])
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Authenticates a user by forwarding credentials to the AI Controller's authentication endpoint.
    """
    auth_service_url = f"{AI_CONTROLLER_API_BASE_URL}/auth/login" # AI Controller's auth endpoint
    
    try:
        async with aiohttp.ClientSession() as session:
            # Send credentials as JSON to the AI Controller's new authentication endpoint
            # Note: AI Controller's /auth/login expects JSON body (LoginRequest Pydantic model)
            async with session.post(auth_service_url, json={"username": username, "password": password}, timeout=10) as resp:
                if resp.status == status.HTTP_200_OK:
                    auth_response = await resp.json()
                    jwt_token = auth_response.get("access_token") 
                    if jwt_token:
                        return {"access_token": jwt_token, "token_type": "bearer"}
                    else:
                        logger.error("Mobile API: AI Controller login response missing access_token.")
                        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication service error: Missing token.")
                elif resp.status == status.HTTP_401_UNAUTHORIZED:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
                else:
                    response_text = await resp.text()
                    logger.error(f"Mobile API: AI Controller login failed with status {resp.status}: {response_text}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Authentication service error: {response_text}")
    except aiohttp.ClientError as e:
        logger.error(f"Mobile API: Failed to connect to AI Controller auth service at {auth_service_url}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service unreachable.")
    except asyncio.TimeoutError:
        logger.error(f"Mobile API: Timeout connecting to AI Controller auth service at {auth_service_url}.")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Authentication service timed out.")
    except Exception as e:
        logger.error(f"Mobile API: Unexpected error during login process: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Login process failed unexpectedly: {e}")