import random
from datetime import datetime, timedelta
import logging # <--- ADD THIS

logger = logging.getLogger(__name__)

class EnergyOptimizer:
    def __init__(self):
        self.energy_prices = self._get_hourly_energy_prices()
        self.comfort_weight = 0.7 # Weight for comfort (higher means comfort is more prioritized)
        self.energy_weight = 0.3 # Weight for energy cost (higher means energy cost is more prioritized)
        logger.info("EnergyOptimizer initialized.")
        
    def _get_hourly_energy_prices(self):
        """
        Simulates time-of-use energy pricing for a 24-hour cycle.
        Prices are typically higher during peak demand hours.
        """
        base_price = 0.12  # $/kWh (e.g., off-peak rate)
        # Define peak and off-peak hours
        # Example: 4 PM - 8 PM (16:00-20:00) are 1.5x base price
        # Example: 2 AM - 6 AM (02:00-06:00) are 0.8x base price
        return {
            hour: base_price * (1.5 if 16 <= hour <= 20 else 0.8 if 2 <= hour <= 6 else 1.0)
            for hour in range(24)
        }
    
    def optimize_schedule(self, current_temp: float, target_temp: float, 
                        predicted_temps: list, occupancy_schedule: list) -> list:
        """
        Optimizes the HVAC schedule for the next predicted period (e.g., next 24 hours)
        balancing comfort and energy cost.
        :param current_temp: The current ambient temperature.
        :param target_temp: The desired target temperature for comfort.
        :param predicted_temps: A list of predicted temperatures for future hours.
        :param occupancy_schedule: A list of boolean values (True if occupied, False otherwise)
                                for future hours, corresponding to `predicted_temps`.
        :return: A list of dictionaries, each suggesting an optimal action for a future hour.
        """
        if not predicted_temps or not occupancy_schedule:
            logger.warning("Missing predicted temperatures or occupancy schedule for optimization. Returning empty schedule.")
            return []

        # Ensure schedules are of the same length to avoid index errors
        min_len = min(len(predicted_temps), len(occupancy_schedule))
        predicted_temps = predicted_temps[:min_len]
        occupancy_schedule = occupancy_schedule[:min_len]

        optimal_schedule = []
        
        for i, (pred_temp, occupancy) in enumerate(zip(predicted_temps, occupancy_schedule)):
            current_relative_hour = (datetime.now().hour + i) % 24 # Calculate the actual hour of the day
            energy_price = self.energy_prices.get(current_relative_hour, self.energy_prices[datetime.now().hour]) # Fallback to current hour's price if not found
            
            # Calculate discomfort/comfort score: absolute difference from target
            # Discomfort is weighted more heavily when the space is occupied.
            temp_diff = abs(pred_temp - target_temp)
            comfort_score = temp_diff * (1.5 if occupancy else 0.5) # Higher multiplier for occupied times
            
            # Estimate energy needed: A simplified linear model (e.g., 0.1 kWh per degree-hour difference)
            # In reality, this depends on HVAC efficiency, insulation, outside temperature, etc.
            energy_needed_per_hour = max(0, temp_diff * 0.1 * (1 if occupancy else 0.5)) # Less energy "needed" if unoccupied (less urgency)
            energy_cost = energy_needed_per_hour * energy_price
            
            # Combined optimization score: a weighted sum of comfort and energy cost
            # The goal is to minimize this score.
            total_score = (self.comfort_weight * comfort_score) + (self.energy_weight * energy_cost)
            
            # Decision logic: Should HVAC actively run or be off?
            should_run = False
            if occupancy and temp_diff > 1.0: # If occupied and temperature is significantly off target
                should_run = True
            elif energy_price < 0.10 and temp_diff > 0.5: # If energy is very cheap, consider pre-heating/cooling even if less critical temp diff
                should_run = True
            
            # Determine "intensity" of operation (e.g., how aggressively to run)
            # Higher `total_score` (more discomfort/cost) implies higher intensity if running.
            intensity = min(1.0, total_score * 0.2) if should_run else 0.0 # Scale score to a 0-1 intensity
            
            optimal_schedule.append({
                "hour": current_relative_hour,
                "should_run": should_run,
                "intensity": round(intensity, 2),
                "predicted_temp": round(pred_temp, 2),
                "energy_cost_estimate": round(energy_cost, 3),
                "comfort_score": round(comfort_score, 2),
                "is_occupied": occupancy
            })
            
        logger.debug(f"Generated optimized schedule for {min_len} hours.")
        return optimal_schedule