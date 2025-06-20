# app/models/schemas/common.py
"""Common Pydantic schemas used across the application."""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar('T')

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        str_strip_whitespace = True


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Pagination parameters."""
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class SensorReading(BaseModel):
    """Individual sensor reading."""
    value: float
    unit: str
    accuracy: Optional[float] = None
    status: str = "normal"
    timestamp: Optional[datetime] = None


class DeviceInfo(BaseModel):
    """Basic device information."""
    device_id: str
    name: str
    device_type: str = "thermostat"
    location: Optional[str] = None
    firmware_version: Optional[str] = None