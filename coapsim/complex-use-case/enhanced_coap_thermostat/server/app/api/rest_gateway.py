# server/app/api/rest_gateway.py
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import jwt
import os
import time
import logging

# Import services that the API will interact with
from services.thermostat_service import ThermostatControlService
from services.prediction_service import PredictionService
from services.maintenance_service import MaintenanceService
from database.influxdb_client import InfluxDBClient
from coap.client import EnhancedCoAPClient
from config import ServerConfig

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Smart Thermostat AI API", version="2.0.0")

# Security schema for JWT
security = HTTPBearer()

# Pydantic models for request/response bodies
class ThermostatCommand(BaseModel):
    action: str # e.g., "heat", "cool", "off", "set_target"
    target_temperature: Optional[float] = None
    mode: Optional[str] = None # e.g., "auto", "heat", "cool", "off"
    fan_speed: Optional[str] = None # e.g., "low", "medium", "high", "auto"

class ScheduleEntry(BaseModel):
    time: str # e.g., "08:00"
    temperature: float
    days: List[str] # e.g., ["Mon", "Tue"]
    enabled: bool = True

class UserPreferences(BaseModel):
    comfort_temperature: float = 22.0
    energy_saving_mode: bool = False
    notifications_enabled: bool = True
    auto_mode_enabled: bool = True

# --- Dependency Injection (Services will be injected via FastAPI's state) ---
# When uvicorn starts, our main.py will put instantiated services into app.state
# We define them here as functions for FastAPI's Dependency Injection system
# This way, the FastAPI endpoints can access the *same instances* of services
# that the main control loop is using.
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

# --- JWT Token Verification ---
# This function will be used as a dependency for protected endpoints
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifies the JWT token from the Authorization header."""
    try:
        config = ServerConfig() # Load config to get JWT_SECRET
        payload = jwt.decode(
            credentials.credentials, 
            config.JWT_SECRET, 
            algorithms=["HS256"] # Ensure this matches your token signing algorithm
        )
        # You can add more complex user authorization here based on payload roles/permissions
        # e.g., if payload.get("role") != "admin": raise HTTPException(...)
        return payload # Returns the decoded token payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token received.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token verification error.")

# --- API Endpoints ---

@app.get("/status/{device_id}", response_model=Dict[str, Any])
async def get_device_status(device_id: str, 
                            user: Dict = Depends(verify_token), # Protect with JWT
                            coap_client: EnhancedCoAPClient = Depends(get_coap_client)):
    """
    Retrieves the current status and sensor data of a specific thermostat device.
    """
    logger.info(f"API: User {user.get('sub')} requesting status for device {device_id}")
    device_data = await coap_client.get_device_status()
    sensor_data = await coap_client.get_all_sensor_data()

    if not device_data or not sensor_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found or offline.")

    # Merge data from both resources if needed for a unified response
    full_data = {**device_data, **sensor_data}
    
    # You might want to filter this data to only include relevant fields for mobile.
    return full_data

@app.post("/control/{device_id}", response_model=Dict[str, Any])
async def send_control_command(device_id: str, 
                               command: ThermostatCommand, 
                               user: Dict = Depends(verify_token), # Protect with JWT
                               thermostat_service: ThermostatControlService = Depends(get_thermostat_service)):
    """
    Sends a control command to the thermostat device.
    This bypasses the AI model and directly instructs the device.
    """
    logger.info(f"API: User {user.get('sub')} sending command {command.dict()} to device {device_id}")
    try:
        # Construct a 'decision-like' object for the thermostat_service's execute_decision method
        # This allows reusing the CoAP sending logic
        mock_decision = {
            "action": command.action,
            "target_temperature": command.target_temperature,
            "mode": command.mode or "manual", # Assume "manual" if controlled via API
            "fan_speed": command.fan_speed or "auto",
            "reasoning": [f"Manual control via API by user {user.get('sub')}."],
            "confidence": 1.0 # High confidence as it's a direct command
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
                                      user: Dict = Depends(verify_token), # Protect with JWT
                                      prediction_service: PredictionService = Depends(get_prediction_service)):
    """
    Retrieves temperature predictions for the next few hours for a specific device.
    """
    logger.info(f"API: User {user.get('sub')} requesting {hours}-hour predictions for device {device_id}")
    # Note: Current prediction_service does not filter by device_id for historical_data.
    # It assumes a general model. For per-device predictions, `get_recent_data` in InfluxDB
    # client would need a device_id filter.
    predictions_data = await prediction_service.get_predictions(hours_ahead=hours)
    
    if predictions_data:
        predictions_data["device_id"] = device_id # Add device_id to response
        return predictions_data
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Predictions not available.")

@app.get("/maintenance/{device_id}", response_model=Dict[str, Any])
async def get_device_maintenance_status(device_id: str, 
                                        user: Dict = Depends(verify_token), # Protect with JWT
                                        maintenance_service: MaintenanceService = Depends(get_maintenance_service),
                                        coap_client: EnhancedCoAPClient = Depends(get_coap_client)):
    """
    Retrieves predictive maintenance recommendations and status for a specific device.
    """
    logger.info(f"API: User {user.get('sub')} requesting maintenance status for device {device_id}")
    # Get the latest device status to feed to maintenance service
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
                          user: Dict = Depends(verify_token), # Protect with JWT
                          influx_client: InfluxDBClient = Depends(get_influxdb_client)):
    """
    Retrieves historical energy consumption data for a specific device.
    """
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
    
    # Process the raw data into a more digestible format for the API response
    processed_daily_data = []
    total_consumption_kwh = 0.0
    for entry in energy_data_list:
        # Assuming 'value' is kWh for that measurement point, aggregate by day if needed
        # For simplicity, let's just use the raw points and calculate sum/avg
        processed_daily_data.append({
            "timestamp": entry['time'],
            "consumption_kwh": round(entry['value'], 2)
        })
        total_consumption_kwh += entry['value']

    average_daily_kwh = total_consumption_kwh / days if days > 0 else 0.0
    # Simple projection: average daily cost * 30 days * avg energy price (mock)
    cost_projection_monthly_usd = average_daily_kwh * 30 * 0.15 # Assuming $0.15/kWh avg
    
    return {
        "daily_data": processed_daily_data, # This would ideally be aggregated daily
        "total_consumption_kwh": round(total_consumption_kwh, 2),
        "average_daily_kwh": round(average_daily_kwh, 2),
        "cost_projection_monthly_usd": round(cost_projection_monthly_usd, 2),
        "device_id": device_id
    }

# Placeholder for device registration (if you have a PostgreSQL for device metadata)
# @app.post("/devices", response_model=DeviceInfo)
# async def register_device(...): ...

# Placeholder for schedule management (would interact with database / device)
# @app.post("/schedule/{device_id}")
# async def set_schedule(...): ...