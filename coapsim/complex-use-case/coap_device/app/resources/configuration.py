# client/app/resources/configuration.py
import json
import aiocoap
from aiocoap.resource import Resource
import logging

logger = logging.getLogger(__name__)

class ConfigurationResource(Resource):
    """CoAP resource to get and update device configuration."""
    def __init__(self, device_config):
        super().__init__()
        self.device_config = device_config
        logger.info("ConfigurationResource initialized.")

    async def render_get(self, request):
        """Handle GET request to retrieve current configuration."""
        config_data = {
            "device_id": self.device_config.DEVICE_ID,
            "sensor_update_interval": self.device_config.SENSOR_UPDATE_INTERVAL,
            "enable_occupancy_sensor": self.device_config.ENABLE_OCCUPANCY_SENSOR,
            "enable_air_quality_sensor": self.device_config.ENABLE_AIR_QUALITY_SENSOR,
            "firmware_version": self.device_config.FIRMWARE_VERSION,
            "enable_dtls": self.device_config.ENABLE_DTLS
            # Add other configurable parameters here
        }
        payload = json.dumps(config_data).encode('utf-8')
        logger.info(f"GET /config - Responding with: {config_data}")
        return aiocoap.Message(payload=payload, content_format=50) # JSON format

    async def render_post(self, request):
        """Handle POST request to update configuration."""
        try:
            config_update = json.loads(request.payload.decode('utf-8'))
            response_data = {"status": "success", "message": "Configuration updated", "changes": []}

            if "sensor_update_interval" in config_update:
                new_interval = int(config_update["sensor_update_interval"])
                if 1 <= new_interval <= 300: # Sanity check
                    old_interval = self.device_config.SENSOR_UPDATE_INTERVAL
                    self.device_config.SENSOR_UPDATE_INTERVAL = new_interval
                    response_data["changes"].append(f"Sensor interval: {old_interval}s -> {new_interval}s")
                    logger.info(f"Updated sensor_update_interval to {new_interval}")
                else:
                    raise ValueError("Sensor interval out of range (1-300).")
            
            if "enable_occupancy_sensor" in config_update:
                old_status = self.device_config.ENABLE_OCCUPANCY_SENSOR
                self.device_config.ENABLE_OCCUPANCY_SENSOR = bool(config_update["enable_occupancy_sensor"])
                response_data["changes"].append(f"Occupancy sensor enabled: {old_status} -> {self.device_config.ENABLE_OCCUPANCY_SENSOR}")
                logger.info(f"Updated enable_occupancy_sensor to {self.device_config.ENABLE_OCCUPANCY_SENSOR}")


            payload = json.dumps(response_data).encode('utf-8')
            return aiocoap.Message(payload=payload, content_format=50)

        except Exception as e:
            logger.error(f"Error processing config update: {e}")
            error_payload = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
            return aiocoap.Message(payload=error_payload, code=aiocoap.Code.BAD_REQUEST, content_format=50)