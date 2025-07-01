# server/app/models/energy_optimizer.py
"""Your EnergyOptimizer - keep exactly as provided"""
import random
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class EnergyOptimizer:
    def __init__(self):
        self.energy_prices = self._get_hourly_energy_prices()
        self.comfort_weight = 0.7
        self.energy_weight = 0.3
        logger.info("EnergyOptimizer initialized.")
        
    def _get_hourly_energy_prices(self):
        """Simulate time-of-use energy pricing for a 24-hour cycle"""
        base_price = 0.12  # $/kWh
        return {
            hour: base_price * (1.5 if 16 <= hour <= 20 else 0.8 if 2 <= hour <= 6 else 1.0)
            for hour in range(24)
        }
    
    def optimize_schedule(self, current_temp: float, target_temp: float, 
                        predicted_temps: list, occupancy_schedule: list) -> list:
        """Optimize the HVAC schedule balancing comfort and energy cost"""
        if not predicted_temps or not occupancy_schedule:
            logger.warning("Missing predicted temperatures or occupancy schedule for optimization")
            return []

        min_len = min(len(predicted_temps), len(occupancy_schedule))
        predicted_temps = predicted_temps[:min_len]
        occupancy_schedule = occupancy_schedule[:min_len]

        optimal_schedule = []
        
        for i, (pred_temp, occupancy) in enumerate(zip(predicted_temps, occupancy_schedule)):
            current_relative_hour = (datetime.now().hour + i) % 24
            energy_price = self.energy_prices.get(current_relative_hour, self.energy_prices[datetime.now().hour])
            
            temp_diff = abs(pred_temp - target_temp)
            comfort_score = temp_diff * (1.5 if occupancy else 0.5)
            
            energy_needed_per_hour = max(0, temp_diff * 0.1 * (1 if occupancy else 0.5))
            energy_cost = energy_needed_per_hour * energy_price
            
            total_score = (self.comfort_weight * comfort_score) + (self.energy_weight * energy_cost)
            
            should_run = False
            if occupancy and temp_diff > 1.0:
                should_run = True
            elif energy_price < 0.10 and temp_diff > 0.5:
                should_run = True
            
            intensity = min(1.0, total_score * 0.2) if should_run else 0.0
            
            optimal_schedule.append({
                "hour": current_relative_hour,
                "should_run": should_run,
                "intensity": round(intensity, 2),
                "predicted_temp": round(pred_temp, 2),
                "energy_cost_estimate": round(energy_cost, 3),
                "comfort_score": round(comfort_score, 2),
                "is_occupied": occupancy
            })
            
        logger.debug(f"Generated optimized schedule for {min_len} hours")
        return optimal_schedule