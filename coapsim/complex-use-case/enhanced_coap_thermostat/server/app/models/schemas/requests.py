
# app/models/schemas/requests.py
"""Request schemas for API endpoints."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from .common import BaseSchema


# Authentication requests
class LoginRequest(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50, regex="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Device control requests
class ThermostatCommand(BaseSchema):
    action: str = Field(..., regex="^(on|off|heat|cool|auto)$")
    target_temperature: Optional[float] = Field(None, ge=10, le=35)
    mode: Optional[str] = Field(None, regex="^(heat|cool|auto|off)$")
    fan_speed: Optional[str] = Field(None, regex="^(low|medium|high|auto)$")
    
    @validator('target_temperature')
    def validate_temperature_with_action(cls, v, values):
        action = values.get('action')
        if action in ['heat', 'cool'] and v is None:
            raise ValueError(f'target_temperature is required for action: {action}')
        return v


class ScheduleEntry(BaseSchema):
    time: str = Field(..., regex="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    temperature: float = Field(..., ge=10, le=35)
    days: List[str] = Field(..., min_items=1)
    enabled: bool = True
    
    @validator('days')
    def validate_days(cls, v):
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in v:
            if day.lower() not in valid_days:
                raise ValueError(f'Invalid day: {day}')
        return [day.lower() for day in v]


# Device management requests
class DeviceRegistrationRequest(BaseSchema):
    device_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    configuration: Optional[Dict[str, Any]] = None


class DeviceUpdateRequest(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    configuration: Optional[Dict[str, Any]] = None


# Notification requests
class FCMTokenRequest(BaseSchema):
    token: str = Field(..., min_length=50)
    platform: str = Field(default="web", regex="^(web|android|ios)$")
    device_info: Optional[Dict[str, str]] = None
    user_info: Optional[Dict[str, str]] = None


class NotificationRequest(BaseSchema):
    title: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1, max_length=500)
    data: Optional[Dict[str, Any]] = None
    priority: str = Field(default="normal", regex="^(low|normal|high)$")
    target_tokens: Optional[List[str]] = None


class TestNotificationRequest(BaseSchema):
    title: str = Field(default="Test Notification", max_length=100)
    body: str = Field(default="This is a test notification", max_length=500)
    validate_tokens: bool = True


# ML and prediction requests
class PredictionRequest(BaseSchema):
    hours_ahead: int = Field(default=24, ge=1, le=168)
    include_confidence: bool = True
    include_reasoning: bool = False


class ModelRetrainingRequest(BaseSchema):
    force_retrain: bool = False
    training_hours: int = Field(default=720, ge=24, le=8760)  # 30 days default, max 1 year


# Maintenance requests
class MaintenanceScheduleRequest(BaseSchema):
    preferred_date: Optional[datetime] = None
    priority: str = Field(default="medium", regex="^(low|medium|high|critical)$")
    notes: Optional[str] = Field(None, max_length=500)

