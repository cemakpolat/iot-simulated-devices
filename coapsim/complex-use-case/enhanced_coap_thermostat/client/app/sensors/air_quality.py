import random
import time 
from typing import Dict, Union

# client/app/sensors/air_quality.py
class AirQualitySensor:
    def __init__(self, device_id: str):
        self.device_id = device_id
        
    def read(self) -> Dict[str, Union[float, int, str]]:
        pm2_5 = random.uniform(5, 25)
        pm10 = pm2_5 * random.uniform(1.2, 2.0)
        co2 = random.uniform(400, 800)
        
        # Simulate poor air quality events
        if random.random() < 0.05:
            pm2_5 *= random.uniform(2, 4)
            pm10 *= random.uniform(2, 4)
            co2 *= random.uniform(1.5, 2.5)
            
        aqi = self._calculate_aqi(pm2_5, pm10, co2)
        
        return {
            "pm2_5": round(pm2_5, 1),
            "pm10": round(pm10, 1),
            "co2": round(co2, 0),
            "aqi": aqi,
            "quality": self._get_quality_level(aqi),
            "timestamp": time.time()
        }
    
    def _calculate_aqi(self, pm2_5: float, pm10: float, co2: float) -> int:
        # Simplified AQI calculation
        pm2_5_aqi = min(pm2_5 * 4, 300)
        pm10_aqi = min(pm10 * 2, 300)
        co2_aqi = min((co2 - 400) * 0.2, 100)
        return int(max(pm2_5_aqi, pm10_aqi, co2_aqi))
    
    def _get_quality_level(self, aqi: int) -> str:
        if aqi <= 50:
            return "good"
        elif aqi <= 100:
            return "moderate"
        elif aqi <= 150:
            return "unhealthy_sensitive"
        else:
            return "unhealthy"