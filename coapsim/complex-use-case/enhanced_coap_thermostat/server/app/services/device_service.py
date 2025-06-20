# app/services/device_service.py
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseService
from ..core.exceptions import DeviceNotFoundError, DeviceOfflineError
from ..models.schemas.responses import DeviceStatusResponse, SensorDataResponse
from ..models.schemas.requests import ThermostatCommand
from ..infrastructure.external.coap_client import EnhancedCoAPClient
from ..infrastructure.database.redis import RedisClient
from ..utils.validators import DeviceValidator

class DeviceService(BaseService):
    """Service for managing device communication and operations."""
    
    def __init__(self, coap_client: EnhancedCoAPClient, redis_client: RedisClient):
        super().__init__()
        self.coap_client = coap_client
        self.redis_client = redis_client
        self.validator = DeviceValidator()
        self._device_cache_ttl = 30  # seconds
    
    async def initialize(self) -> bool:
        """Initialize device service."""
        try:
            await self.redis_client.connect()
            self.logger.info("Device service initialized successfully")
            return await super().initialize()
        except Exception as e:
            self.logger.error(f"Failed to initialize device service: {e}")
            return False
    
    async def get_device_status(self, device_id: str) -> DeviceStatusResponse:
        """Get comprehensive device status with caching."""
        self._validate_initialized()
        self.validator.validate_device_id(device_id)
        
        # Try cache first
        cache_key = f"device_status:{device_id}"
        cached_data = await self.redis_client.get_json(cache_key)
        
        if cached_data:
            self.logger.debug(f"Serving cached status for device {device_id}")
            return DeviceStatusResponse(**cached_data)
        
        # Fetch from device
        try:
            device_data = await self.coap_client.get_device_status()
            sensor_data = await self.coap_client.get_all_sensor_data()
            
            if not device_data or not sensor_data:
                raise DeviceOfflineError(f"Device {device_id} is offline or not responding")
            
            # Combine and format data
            status = DeviceStatusResponse(
                device_id=device_id,
                online=True,
                current_temperature=sensor_data.get("temperature", {}).get("value", 0.0),
                target_temperature=device_data.get("target_temperature", 22.0),
                humidity=sensor_data.get("humidity", {}).get("value", 0.0),
                hvac_state=device_data.get("hvac_state", "off"),
                mode=device_data.get("mode", "auto"),
                fan_speed=device_data.get("fan_speed", "auto"),
                last_updated=datetime.now()
            )
            
            # Cache the result
            await self.redis_client.set_json(cache_key, status.dict(), ex=self._device_cache_ttl)
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting device status: {e}")
            if "timeout" in str(e).lower():
                raise DeviceOfflineError(f"Device {device_id} connection timeout")
            else:
                raise DeviceNotFoundError(f"Could not reach device {device_id}")
    
    async def send_command(self, device_id: str, command: ThermostatCommand) -> Dict[str, Any]:
        """Send control command to device with validation."""
        self._validate_initialized()
        self.validator.validate_device_id(device_id)
        self.validator.validate_command(command.dict())
        
        try:
            # Convert Pydantic model to CoAP command format
            coap_command = {
                "hvac_state": command.action,
                "target_temperature": command.target_temperature,
                "mode": command.mode or "auto",
                "fan_speed": command.fan_speed or "auto"
            }
            
            success = await self.coap_client.send_control_command(coap_command)
            
            if not success:
                raise DeviceOfflineError(f"Failed to send command to device {device_id}")
            
            # Invalidate cache to force fresh data on next request
            cache_key = f"device_status:{device_id}"
            await self.redis_client.delete(cache_key)
            
            result = {
                "success": True,
                "device_id": device_id,
                "command": command.dict(),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Command sent successfully to {device_id}: {command.action}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending command to device {device_id}: {e}")
            raise DeviceOfflineError(f"Could not send command to device {device_id}: {str(e)}")
    
    async def get_sensor_data(self, device_id: str) -> SensorDataResponse:
        """Get current sensor data from device."""
        self._validate_initialized()
        self.validator.validate_device_id(device_id)
        
        try:
            sensor_data = await self.coap_client.get_all_sensor_data()
            
            if not sensor_data:
                raise DeviceOfflineError(f"No sensor data available from device {device_id}")
            
            return SensorDataResponse(
                temperature=sensor_data.get("temperature", {}).get("value", 0.0),
                humidity=sensor_data.get("humidity", {}).get("value", 0.0),
                air_quality=sensor_data.get("air_quality", {}),
                occupancy=sensor_data.get("occupancy", {}),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting sensor data from device {device_id}: {e}")
            raise DeviceNotFoundError(f"Could not get sensor data from device {device_id}")
    
    async def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get list of all registered devices."""
        # This would typically query the database
        # For now, return mock data
        return [
            {
                "device_id": "thermostat-01",
                "name": "Living Room Thermostat",
                "type": "thermostat",
                "online": True,
                "last_seen": datetime.now().isoformat()
            }
        ]
    
    async def cleanup(self):
        """Cleanup device service resources."""
        try:
            await self.redis_client.disconnect()
            await super().cleanup()
        except Exception as e:
            self.logger.error(f"Error during device service cleanup: {e}")

