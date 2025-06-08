import json
import aiocoap
from aiocoap.resource import Resource
# client/app/resources/control.py
class EnhancedControlResource(Resource):
    def __init__(self):
        super().__init__()
        self.hvac_state = "off"
        self.target_temperature = 22.0
        self.mode = "auto"  # auto, heat, cool, off
        self.fan_speed = "auto"  # low, medium, high, auto
        
    async def render_post(self, request):
        try:
            command_data = json.loads(request.payload.decode())
            response_data = {"status": "success", "changes": []}
            
            if "hvac_state" in command_data:
                old_state = self.hvac_state
                self.hvac_state = command_data["hvac_state"]
                response_data["changes"].append(f"HVAC: {old_state} → {self.hvac_state}")
                
            if "target_temperature" in command_data:
                old_temp = self.target_temperature
                self.target_temperature = float(command_data["target_temperature"])
                response_data["changes"].append(f"Target: {old_temp}°C → {self.target_temperature}°C")
                
            if "mode" in command_data:
                old_mode = self.mode
                self.mode = command_data["mode"]
                response_data["changes"].append(f"Mode: {old_mode} → {self.mode}")
                
            if "fan_speed" in command_data:
                old_fan = self.fan_speed
                self.fan_speed = command_data["fan_speed"]
                response_data["changes"].append(f"Fan: {old_fan} → {self.fan_speed}")
                
            response_data["current_state"] = {
                "hvac_state": self.hvac_state,
                "target_temperature": self.target_temperature,
                "mode": self.mode,
                "fan_speed": self.fan_speed
            }
            
        except Exception as e:
            response_data = {"status": "error", "message": str(e)}
            
        payload = json.dumps(response_data).encode('utf-8')
        return aiocoap.Message(payload=payload, content_format=50)