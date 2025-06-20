# app/infrastructure/monitoring/health_checker.py
"""System health monitoring."""

import asyncio
import logging
import psutil
from datetime import datetime
from typing import Dict, Any, List

from ...core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthChecker:
    """System health monitoring service."""
    
    def __init__(self):
        self.checks = {}
        self.thresholds = {
            "cpu_usage": 90.0,
            "memory_usage": 90.0,
            "disk_usage": 95.0,
            "temperature_variance": 5.0
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information."""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {},
            "warnings": [],
            "critical_issues": []
        }
        
        # System resource checks
        health_data["checks"]["system"] = await self._check_system_resources()
        
        # Service health checks
        health_data["checks"]["services"] = await self._check_services()
        
        # Database connectivity
        health_data["checks"]["databases"] = await self._check_databases()
        
        # External services
        health_data["checks"]["external"] = await self._check_external_services()
        
        # Determine overall status
        health_data = self._determine_overall_status(health_data)
        
        return health_data
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources (CPU, memory, disk)."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent,
                "status": "healthy" if all([
                    cpu_percent < self.thresholds["cpu_usage"],
                    memory.percent < self.thresholds["memory_usage"],
                    disk.percent < self.thresholds["disk_usage"]
                ]) else "warning"
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _check_services(self) -> Dict[str, Any]:
        """Check internal service health."""
        services = {
            "device_service": "unknown",
            "ml_service": "unknown", 
            "notification_service": "unknown",
            "background_tasks": "unknown"
        }
        
        # This would check actual service instances
        # For now, return mock data
        return {
            "services": services,
            "status": "healthy"
        }
    
    async def _check_databases(self) -> Dict[str, Any]:
        """Check database connectivity."""
        databases = {
            "postgresql": "unknown",
            "influxdb": "unknown",
            "redis": "unknown"
        }
        
        # This would check actual database connections
        # For now, return mock data
        return {
            "databases": databases,
            "status": "healthy"
        }
    
    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity."""
        services = {
            "coap_device": "unknown",
            "fcm_service": "unknown",
            "email_service": "unknown"
        }
        
        # This would check actual external services
        # For now, return mock data
        return {
            "services": services,
            "status": "healthy"
        }
    
    def _determine_overall_status(self, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall system status based on individual checks."""
        statuses = []
        for check_category in health_data["checks"].values():
            if isinstance(check_category, dict) and "status" in check_category:
                statuses.append(check_category["status"])
        
        if "error" in statuses:
            health_data["status"] = "unhealthy"
        elif "warning" in statuses:
            health_data["status"] = "warning"
        else:
            health_data["status"] = "healthy"
        
        return health_data

