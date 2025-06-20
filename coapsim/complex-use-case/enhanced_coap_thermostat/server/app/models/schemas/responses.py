# app/models/schemas/responses.py
"""Response schemas for API endpoints."""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field
from .common import BaseSchema, TimestampMixin, SensorReading, DeviceInfo

T = TypeVar('T')


class BaseResponse(BaseSchema):
    """Base response with common fields."""
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseResponse):
    """Standard success response."""
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseResponse):
    """Standard error response."""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DataResponse(BaseResponse, Generic[T]):
    """Generic data response."""
    data: T
    message: Optional[str] = None


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated response."""
    data: List[T]
    pagination: Dict[str, Any] = Field(description="Pagination metadata")
    total: int
    pages: int


# Authentication responses
class TokenResponse(BaseSchema):
    """Authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


class UserResponse(BaseSchema, TimestampMixin):
    """User information response."""
    id: str
    username: str
    email: str
    is_active: bool
    roles: List[str] = []
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Device responses
class DeviceStatusResponse(BaseSchema):
    """Comprehensive device status response."""
    device_id: str
    name: str
    online: bool
    current_temperature: float
    target_temperature: float
    humidity: float
    hvac_state: str
    mode: str
    fan_speed: str
    energy_consumption: Optional[float] = None
    uptime_seconds: Optional[int] = None
    firmware_version: Optional[str] = None
    last_updated: datetime
    
    # Additional sensor data
    air_quality: Optional[Dict[str, Any]] = None
    occupancy: Optional[Dict[str, Any]] = None


class SensorDataResponse(BaseSchema):
    """Current sensor data response."""
    device_id: str
    temperature: SensorReading
    humidity: SensorReading
    air_quality: Optional[Dict[str, Any]] = None
    occupancy: Optional[Dict[str, Any]] = None
    timestamp: datetime


class DeviceListResponse(BaseSchema):
    """Device list response."""
    devices: List[DeviceInfo]
    total: int


# ML and prediction responses
class PredictionResponse(BaseSchema):
    """ML prediction response."""
    device_id: str
    predictions: List[float]
    confidence: float = Field(ge=0, le=1)
    model_version: str
    generated_at: datetime
    hours_ahead: int
    reasoning: Optional[List[str]] = None


class AnomalyDetectionResponse(BaseSchema):
    """Anomaly detection response."""
    device_id: str
    anomalies_detected: List[Dict[str, Any]]
    risk_score: float = Field(ge=0, le=1)
    recommendations: List[str]
    analysis_period: str


class ModelStatusResponse(BaseSchema):
    """ML model status response."""
    model_name: str
    is_trained: bool
    last_training: Optional[datetime] = None
    accuracy: Optional[float] = None
    version: str
    training_data_points: Optional[int] = None


# Maintenance responses
class MaintenanceResponse(BaseSchema):
    """Maintenance analysis response."""
    device_id: str
    maintenance_score: int = Field(ge=0, le=100)
    priority: str
    recommendations: List[str]
    estimated_cost: Optional[Dict[str, float]] = None
    next_maintenance_date: Optional[str] = None
    risk_factors: List[str] = []
    last_maintenance: Optional[datetime] = None


# Notification responses
class FCMRegistrationResponse(BaseSchema):
    """FCM token registration response."""
    success: bool
    message: str
    token_count: int
    is_new_registration: bool


class NotificationStatsResponse(BaseSchema):
    """Notification statistics response."""
    total_tokens: int
    active_tokens: int
    invalid_tokens: int
    recent_registrations: int
    last_validation: Optional[datetime] = None


# Energy and optimization responses
class EnergyDataResponse(BaseSchema):
    """Energy consumption data response."""
    device_id: str
    daily_data: List[Dict[str, Any]]
    total_consumption_kwh: float
    average_daily_kwh: float
    cost_projection_monthly_usd: float
    period_start: datetime
    period_end: datetime


class OptimizationResponse(BaseSchema):
    """Energy optimization response."""
    device_id: str
    current_efficiency: float = Field(ge=0, le=1)
    optimization_suggestions: List[str]
    potential_savings_monthly: float
    optimal_schedule: List[Dict[str, Any]]


# Health and monitoring responses
class HealthCheckResponse(BaseSchema):
    """Health check response."""
    status: str
    version: str
    environment: str
    uptime: float
    services: Dict[str, str]
    timestamp: datetime


class MetricsResponse(BaseSchema):
    """System metrics response."""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    requests_per_minute: float
    error_rate: float
    timestamp: datetime