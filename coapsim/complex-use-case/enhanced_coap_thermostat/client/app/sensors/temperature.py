# client/app/sensors/temperature.py
import random
import time
from typing import Dict, Optional
from dataclasses import dataclass
import math

@dataclass
class TemperatureReading:
    value: float
    timestamp: float
    unit: str = "celsius"
    accuracy: float = 0.1
    calibration_offset: float = 0.0

class AdvancedTemperatureSensor:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.calibration_offset = 0.0
        # self.drift_factor = random.uniform(-0.001, 0.001) # Remove or significantly reduce this for more realistic temp
        self.last_reading = None
        
    def read(self) -> TemperatureReading:
        # Simulate realistic temperature variations around a base
        base_temp = 22.0 + random.uniform(-2, 3)
        
        # Add time-based variations (daily cycle)
        # Assuming typical home thermostat behavior
        current_time_in_seconds = time.time()
        # Convert seconds to hours for a 24-hour cycle
        hour_of_day = (current_time_in_seconds % (24 * 3600)) / 3600 
        
        # Simulate a daily temperature swing (e.g., cooler at night, warmer during day)
        # Shift sine wave so peak/trough align with typical day/night cycle
        # e.g., lowest at 5 AM, highest at 5 PM
        daily_variation = 3 * math.sin((hour_of_day - 5) * math.pi / 12) 
        
        # Simulate a very slow, subtle drift if desired (e.g., over days/weeks, not seconds)
        # A drift of 0.001 per day. Divide by 24*3600 to make it per second.
        # This will be very subtle over short runs.
        subtle_drift_per_second = random.uniform(-0.0000001, 0.0000001) 
        drift = subtle_drift_per_second * current_time_in_seconds 
        
        # Simulate occasional anomalies (2% chance of a temporary spike)
        if random.random() < 0.02:
            # Short, sharp anomaly, e.g., oven on, or window open
            anomaly_magnitude = random.uniform(2, 5) # Smaller, more realistic spike
            base_temp += anomaly_magnitude
            
        final_temp = base_temp + daily_variation + drift + self.calibration_offset
        
        reading = TemperatureReading(
            value=round(final_temp, 2),
            timestamp=time.time(),
            accuracy=0.1
        )
        
        self.last_reading = reading
        return reading