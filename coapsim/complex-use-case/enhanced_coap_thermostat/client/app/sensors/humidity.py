import random
import time 
from typing import Dict
# client/app/sensors/humidity.py
class HumiditySensor:
    def __init__(self, device_id: str):
        self.device_id = device_id
        
    def read(self) -> Dict:
        base_humidity = random.uniform(35, 65)
        if random.random() < 0.03:  # Occasional high humidity
            base_humidity = random.uniform(70, 90)
            
        return {
            "value": round(base_humidity, 1),
            "unit": "percent",
            "timestamp": time.time(),
            "status": "normal" if base_humidity < 70 else "high"
        }
