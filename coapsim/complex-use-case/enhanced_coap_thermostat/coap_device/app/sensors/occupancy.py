import random
import time 
from typing import Dict

# client/app/sensors/occupancy.py
class OccupancySensor:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.occupancy_probability = 0.3  # Base probability
        
    def read(self) -> Dict:
        # Time-based occupancy simulation
        hour = time.localtime().tm_hour
        if 7 <= hour <= 9 or 17 <= hour <= 22:  # Morning/evening
            self.occupancy_probability = 0.8
        elif 9 <= hour <= 17:  # Work hours
            self.occupancy_probability = 0.2
        else:  # Night
            self.occupancy_probability = 0.9
            
        is_occupied = random.random() < self.occupancy_probability
        confidence = random.uniform(0.8, 1.0) if is_occupied else random.uniform(0.7, 0.95)
        
        return {
            "occupied": is_occupied,
            "confidence": round(confidence, 2),
            "motion_detected": is_occupied and random.random() < 0.8,
            "timestamp": time.time()
        }