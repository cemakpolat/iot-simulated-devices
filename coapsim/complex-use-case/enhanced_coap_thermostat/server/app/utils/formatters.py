# app/utils/formatters.py
"""Response formatting utilities."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json


class ResponseFormatter:
    """Utilities for formatting API responses."""
    
    @staticmethod
    def format_success_response(message: str, data: Optional[Any] = None) -> Dict[str, Any]:
        """Format a standard success response."""
        response = {
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if data is not None:
            response["data"] = data
        
        return response
    
    @staticmethod
    def format_error_response(error: str, error_code: Optional[str] = None, 
                            details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format a standard error response."""
        response = {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        if error_code:
            response["error_code"] = error_code
        
        if details:
            response["details"] = details
        
        return response
    
    @staticmethod
    def format_paginated_response(data: List[Any], total: int, skip: int, limit: int) -> Dict[str, Any]:
        """Format a paginated response."""
        return {
            "success": True,
            "data": data,
            "pagination": {
                "total": total,
                "count": len(data),
                "skip": skip,
                "limit": limit,
                "has_next": skip + limit < total,
                "has_prev": skip > 0
            },
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_device_status(status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format device status for API response."""
        formatted = {
            "device_id": status_data.get("device_id"),
            "online": status_data.get("online", False),
            "current_temperature": status_data.get("temperature", {}).get("value", 0.0),
            "target_temperature": status_data.get("target_temperature", 22.0),
            "humidity": status_data.get("humidity", {}).get("value", 0.0),
            "hvac_state": status_data.get("hvac_state", "off"),
            "mode": status_data.get("mode", "auto"),
            "fan_speed": status_data.get("fan_speed", "auto"),
            "last_updated": datetime.now().isoformat()
        }
        
        # Add optional fields if present
        optional_fields = ["energy_consumption", "uptime_seconds", "firmware_version", "air_quality", "occupancy"]
        for field in optional_fields:
            if field in status_data:
                formatted[field] = status_data[field]
        
        return formatted
    
    @staticmethod
    def format_sensor_reading(value: Union[int, float], unit: str, 
                            accuracy: Optional[float] = None, status: str = "normal") -> Dict[str, Any]:
        """Format individual sensor reading."""
        reading = {
            "value": float(value),
            "unit": unit,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        if accuracy is not None:
            reading["accuracy"] = float(accuracy)
        
        return reading

