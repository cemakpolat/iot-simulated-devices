# app/api/v1/monitoring.py
"""Monitoring and health check endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from datetime import datetime

from ...core.dependencies import get_dependency_manager
from ...models.schemas.responses import HealthCheckResponse, MetricsResponse
from ...infrastructure.monitoring.health_checker import HealthChecker
from ...infrastructure.monitoring.metrics import get_current_metrics
from ...core.config import get_settings

router = APIRouter(prefix="/monitoring")
settings = get_settings()


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Comprehensive health check endpoint."""
    health_checker = HealthChecker()
    health_data = await health_checker.get_system_health()
    
    return {
        "status": health_data["status"],
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": health_data["timestamp"],
        "checks": health_data["checks"],
        "warnings": health_data["warnings"],
        "critical_issues": health_data["critical_issues"]
    }


@router.get("/health/simple")
async def simple_health_check():
    """Simple health check for load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION
    }


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """Get application performance metrics."""
    metrics = get_current_metrics()
    
    return {
        "application": metrics,
        "system": {
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT
        }
    }


@router.get("/status")
async def get_system_status():
    """Get detailed system status."""
    dependency_manager = get_dependency_manager()
    
    services_status = {
        "device_service": "healthy" if dependency_manager.device_service else "unavailable",
        "ml_service": "healthy" if dependency_manager.ml_service else "unavailable",
        "notification_service": "healthy" if dependency_manager.notification_service else "unavailable",
        "postgres": "healthy" if dependency_manager.postgres_client else "unavailable",
        "influxdb": "healthy" if dependency_manager.influx_client else "unavailable",
        "redis": "healthy" if dependency_manager.redis_client else "unavailable",
        "coap_client": "healthy" if dependency_manager.coap_client else "unavailable"
    }
    
    return {
        "application": {
            "name": settings.APP_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "status": "healthy"
        },
        "services": services_status,
        "timestamp": datetime.now().isoformat()
    }
