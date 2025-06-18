# client/app/resources/diagnostics.py
import json
import aiocoap
from aiocoap.resource import Resource
import time
import psutil # Requires psutil in requirements.txt
import logging

logger = logging.getLogger(__name__)

class DiagnosticsResource(Resource):
    """CoAP resource to retrieve device diagnostics and health information."""
    def __init__(self, device_id: str, start_time: float):
        super().__init__()
        self.device_id = device_id
        self.start_time = start_time
        logger.info("DiagnosticsResource initialized.")

    async def render_get(self, request):
        """Handle GET request to retrieve diagnostics data."""
        try:
            uptime_seconds = int(time.time() - self.start_time)
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')

            diagnostics_data = {
                "device_id": self.device_id,
                "timestamp": time.time(),
                "uptime_seconds": uptime_seconds,
                "cpu_usage_percent": cpu_percent,
                "memory_usage": {
                    "total_mb": round(memory_info.total / (1024*1024), 2),
                    "available_mb": round(memory_info.available / (1024*1024), 2),
                    "percent": memory_info.percent
                },
                "disk_usage": {
                    "total_gb": round(disk_info.total / (1024**3), 2),
                    "used_gb": round(disk_info.used / (1024**3), 2),
                    "percent": disk_info.percent
                },
                "network_status": self._get_network_status(),
                "last_error": "None", # Placeholder, would be pulled from a log
                "self_test_status": "Passed" # Placeholder for a self-test function
            }

            payload = json.dumps(diagnostics_data).encode('utf-8')
            logger.info(f"GET /diagnostics - Responding with system diagnostics.")
            return aiocoap.Message(payload=payload, content_format=50)

        except Exception as e:
            logger.error(f"Error gathering diagnostics: {e}")
            error_payload = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
            return aiocoap.Message(payload=error_payload, code=aiocoap.Code.INTERNAL_SERVER_ERROR, content_format=50)
            
    def _get_network_status(self):
        """Simulate network status."""
        # In a real device, this would involve checking interface status, pinging gateway, etc.
        return {
            "ip_address": "127.0.0.1", # Or actual IP
            "connectivity": "online",
            "rssi_dbm": -55 # Wi-Fi signal strength
        }