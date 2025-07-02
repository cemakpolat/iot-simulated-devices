import random
import time
from dataclasses import dataclass
import math

@dataclass
class TemperatureReading:
    value: float
    timestamp: float
    unit: str = "celsius"
    accuracy: float = 0.1 # Represents the typical measurement error (e.g., +/- 0.1C)
    calibration_offset: float = 0.0

class AdvancedTemperatureSensor:
    def __init__(self, device_id: str, initial_temp: float = 21.0, base_accuracy: float = 0.1):
        self.device_id = device_id
        self.calibration_offset = 0.0 # Can be adjusted externally, e.g., for real-world calibration
        self.base_accuracy = base_accuracy # The inherent precision/error margin of the sensor
        
        # --- Internal state for simulating realistic temperature evolution ---
        # This represents the 'true' environmental temperature, which evolves gradually.
        self._current_true_temp = initial_temp 
        self._last_update_time = time.time()
        
        # --- Parameters for temperature dynamics ---
        # Daily cycle parameters
        self._daily_swing_amplitude = 2.5 # Max degrees swing due to daily cycle (e.g., 2.5C difference between peak and trough)
        self._daily_swing_peak_hour = 17.0 # Hour of the day when temperature is typically highest (e.g., 5 PM)
        
        # Inertia factor: how quickly the true temperature adjusts towards its target.
        # A smaller value means more inertia (slower adjustment).
        # This value should be tuned based on how frequently 'read' is called.
        # 0.05 means it closes 5% of the gap to target in one step.
        self._temp_inertia_factor = 0.05 
        
        # Environmental micro-fluctuations (small, unmodeled random walk of true temp)
        self._environmental_noise_std = 0.02 # Standard deviation of random walk per minute
        
        # Long-term sensor drift (very slow, cumulative over hours/days/weeks)
        # This simulates a sensor slowly becoming inaccurate over its lifetime
        self._long_term_drift_rate_per_hour = random.uniform(-0.000005, 0.000005) # Degrees per hour
        
        # --- Anomaly parameters ---
        self._anomaly_probability = 0.01 # 1% chance of a temporary anomaly per reading
        self._anomaly_magnitude_range = (1.5, 4.0) # Range of degrees for an anomaly
        
        self._last_reading = None # Stored for potential future use or debugging
        
    def read(self) -> TemperatureReading:
        current_time = time.time()
        time_elapsed_seconds = current_time - self._last_update_time
        time_elapsed_hours = time_elapsed_seconds / 3600.0
        time_elapsed_minutes = time_elapsed_seconds / 60.0

        # 1. Determine the target environmental temperature based on base and daily cycle
        hour_of_day = (current_time % (24 * 3600)) / 3600.0 # Current hour (0-23.99)

        # Base temperature for the environment (e.g., average room temperature setpoint)
        environmental_base_temp = 22.0 # Can be made dynamic if simulating thermostat schedules

        # Calculate daily cycle variation using a sine wave.
        # Shift the sine wave so its peak aligns with _daily_swing_peak_hour.
        # Sine wave is at its peak when argument is pi/2, lowest at 3pi/2.
        # (hour_of_day - self._daily_swing_peak_hour) * math.pi / 12  -> This shifts the peak.
        # Adding math.pi/2 will make sine peak at `_daily_swing_peak_hour`.
        daily_cycle_variation = self._daily_swing_amplitude * math.sin(
            (hour_of_day - self._daily_swing_peak_hour + 6) * math.pi / 12 # +6 shifts trough to peak
        )
        
        # The ideal target temperature for the environment at this exact moment
        target_environmental_temp = environmental_base_temp + daily_cycle_variation

        # 2. Simulate the true temperature evolving towards its target with inertia
        # The _current_true_temp gradually adjusts towards the target_environmental_temp.
        # Add small random environmental fluctuations (e.g., drafts, sun shifts)
        environmental_fluctuation = random.gauss(0, self._environmental_noise_std) * time_elapsed_minutes
        
        delta_to_target = target_environmental_temp - self._current_true_temp
        self._current_true_temp += delta_to_target * self._temp_inertia_factor + environmental_fluctuation
        
        # Apply long-term sensor drift to the 'true' temperature over time
        self._current_true_temp += self._long_term_drift_rate_per_hour * time_elapsed_hours

        # 3. Simulate occasional, short-lived anomalies
        # These are temporary spikes/drops affecting the *current* reading, not the true long-term temp.
        anomaly_effect = 0.0
        if random.random() < self._anomaly_probability:
            magnitude = random.uniform(*self._anomaly_magnitude_range)
            if random.random() < 0.5: # 50% chance of a drop vs. spike
                magnitude *= -1
            anomaly_effect = magnitude
            # print(f"Anomaly detected! Magnitude: {anomaly_effect:.2f}°C") # For debugging/observing

        # The 'raw' temperature reading before sensor imperfections are applied
        raw_sensor_input_temp = self._current_true_temp + anomaly_effect

        # 4. Add sensor measurement noise/error (based on base_accuracy)
        # Using a Gaussian distribution where 3*sigma is approximately the accuracy margin.
        measurement_noise = random.gauss(0, self.base_accuracy / 3.0) 

        # Final calculated temperature reading value
        final_temp_value = raw_sensor_input_temp + measurement_noise + self.calibration_offset
        
        # Soft clamp to prevent unrealistic extreme values due to noise/drift
        final_temp_value = max(-20.0, min(60.0, final_temp_value)) 

        # Create the TemperatureReading object
        reading = TemperatureReading(
            value=round(final_temp_value, 2), # Round for typical sensor display precision (e.g., 2 decimal places)
            timestamp=current_time,
            accuracy=self.base_accuracy # Report the sensor's inherent accuracy
        )
        
        self._last_reading = reading
        self._last_update_time = current_time # Update last update time for next reading
        return reading
