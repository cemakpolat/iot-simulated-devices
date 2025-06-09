import json
import aiocoap
from aiocoap.resource import Resource
import time
import random

class DeviceStatusResource(Resource):
    def __init__(self, device_id: str):
        super().__init__()
        self.device_id = device_id
        self.start_time = time.time()
        self.hvac_state = "off"
        self.target_temperature = 22.0
        
    async def render_get(self, request):
        uptime = time.time() - self.start_time
        status = {
            "device_id": self.device_id,
            "status": "online",
            "uptime_seconds": int(uptime),
            "hvac_state": self.hvac_state,
            "target_temperature": self.target_temperature,
            "firmware_version": "2.1.0",
            "last_maintenance": time.time() - 86400 * 7,  # 7 days ago
            "energy_consumption": random.uniform(1.2, 2.8),  # kWh
            "timestamp": time.time()
        }
        
        payload = json.dumps(status).encode('utf-8')
        return aiocoap.Message(payload=payload, content_format=50)

