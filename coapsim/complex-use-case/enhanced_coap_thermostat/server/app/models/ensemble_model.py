import numpy as np
import pandas as pd
import logging 
from datetime import datetime, timedelta 
import random 

# Import the actual model classes from their respective files
from .lstm_predictor import LSTMTemperaturePredictor
from .anomaly_detector import AnomalyDetector
from .energy_optimizer import EnergyOptimizer

logger = logging.getLogger(__name__)

class EnsemblePredictor:
    """
    Combines outputs from various ML models (LSTM, Anomaly Detector, Energy Optimizer)
    to make a comprehensive HVAC control decision.
    """
    def __init__(self, lstm_model: LSTMTemperaturePredictor, 
                    anomaly_detector: AnomalyDetector, 
                    energy_optimizer: EnergyOptimizer):
        """
        Initializes the ensemble predictor with injected instances of individual models.
        This promotes loose coupling and testability.
        """
        self.lstm_model = lstm_model
        self.anomaly_detector = anomaly_detector
        self.energy_optimizer = energy_optimizer
        logger.info("EnsemblePredictor initialized with injected models.")

    def make_decision(self, sensor_data: dict, historical_data: pd.DataFrame) -> dict:
        """
        Makes a comprehensive HVAC control decision based on current sensor data
        and historical data, utilizing predictions, anomaly detection, and energy optimization.
        :param sensor_data: Dictionary of current sensor readings and device status.
        :param historical_data: Pandas DataFrame of recent historical sensor data for ML models.
        :return: A dictionary representing the recommended HVAC action and related insights.
        """
        current_temp = sensor_data.get('temperature', {}).get('value')
        occupancy = sensor_data.get('occupancy', {}).get('occupied')
        air_quality_aqi = sensor_data.get('air_quality', {}).get('aqi')

        if current_temp is None or occupancy is None or air_quality_aqi is None:
            logger.error("Missing critical sensor data for decision making. Returning default 'off'.")
            return {
                "action": "off", "target_temperature": 22.0, "mode": "auto", "fan_speed": "auto",
                "reasoning": ["Missing critical sensor data."], "confidence": 0.0,
                "predictions": [], "energy_schedule": []
            }

        # --- 1. Get Temperature Predictions ---
        predicted_temps = self.lstm_model.predict(historical_data, hours_ahead=6)
        if predicted_temps is None or not predicted_temps:
            predicted_temps = [current_temp] * 6 # Fallback to current temp if prediction fails
            logger.warning("LSTM temperature prediction failed or returned no data. Using current temperature as fallback for predictions.")

        # --- 2. Detect Anomalies ---
        temp_anomaly = False
        # Prepare data for anomaly detector (ensure it matches features used in training, e.g., temperature and humidity)
        if 'temperature' in sensor_data and 'humidity' in sensor_data:
            current_features_df = pd.DataFrame([{
                'temperature': sensor_data['temperature']['value'], 
                'humidity': sensor_data['humidity']['value']
            }])
            # Assuming anomaly detector was trained on ['temperature', 'humidity'].
            # Pass the actual feature columns expected by `self.anomaly_detector.predict` method.
            anomaly_prediction = self.anomaly_detector.predict(current_features_df, feature_columns=['temperature', 'humidity'])
            if anomaly_prediction.size > 0:
                temp_anomaly = anomaly_prediction[0] == -1
                if temp_anomaly:
                    logger.warning(f"Temperature anomaly detected for {sensor_data.get('device_id', 'unknown')}: {current_temp}°C")
            else:
                logger.warning("Anomaly detector prediction returned no results.")
        else:
            logger.warning("Insufficient sensor data for comprehensive anomaly detection (needs temp and humidity).")

        # --- 3. Energy Optimization ---
        # Create a simplified occupancy schedule for the optimizer based on current state (e.g., assumes current state for all predicted hours)
        # In a more advanced system, this would come from a learned occupancy pattern or user schedule.
        occupancy_schedule = [occupancy] * len(predicted_temps)  
        optimal_schedule = self.energy_optimizer.optimize_schedule(
            current_temp, 22.0, predicted_temps, occupancy_schedule
        )
        if not optimal_schedule:
            logger.warning("Energy optimization failed to produce a schedule. Providing a default minimal schedule.")
            optimal_schedule = [{"hour": (datetime.now().hour + i) % 24, "should_run": False, "intensity": 0.0} for i in range(len(predicted_temps))]

        # --- 4. Ensemble Decision Logic ---
        # Initialize a default decision
        decision = {
            "action": "off", # Default action
            "target_temperature": 22.0, # Default target
            "mode": "auto",       # Default mode
            "fan_speed": "auto",  # Default fan speed
            "reasoning": [],      # List to explain decision factors
            "confidence": 0.0     # Confidence score (0.0 to 1.0)
        }

        # Influence 1: Temperature-based control (primary comfort)
        if occupancy: # Only react strongly to temperature if occupied
            if current_temp > 25:
                decision["action"] = "cool"
                decision["target_temperature"] = 22.0 # Set a default target
                decision["reasoning"].append("High temperature with occupancy detected.")
                decision["confidence"] += 0.4
            elif current_temp < 20:
                decision["action"] = "heat"
                decision["target_temperature"] = 22.0
                decision["reasoning"].append("Low temperature with occupancy detected.")
                decision["confidence"] += 0.4
        else: # If unoccupied, be less reactive, maybe just turn off or set to a wider range
            if current_temp > 28: # Still cool if it gets excessively hot
                decision["action"] = "cool"
                decision["target_temperature"] = 26.0
                decision["reasoning"].append("Extreme high temperature (unoccupied).")
                decision["confidence"] += 0.1
            elif current_temp < 15: # Or heat if it gets excessively cold
                decision["action"] = "heat"
                decision["target_temperature"] = 18.0
                decision["reasoning"].append("Extreme low temperature (unoccupied).")
                decision["confidence"] += 0.1
            else: # Default to off when unoccupied and within tolerable range
                decision["action"] = "off"
                decision["reasoning"].append("System off (unoccupied, within tolerance).")


        # Influence 2: Air Quality consideration
        if air_quality_aqi > 100: # Threshold for unhealthy air quality
            decision["fan_speed"] = "high" # Run fan more aggressively to circulate air
            decision["reasoning"].append("Poor air quality detected (AQI > 100).")
            decision["confidence"] += 0.2
        elif air_quality_aqi > 50 and decision["fan_speed"] == "auto":
                decision["fan_speed"] = "medium"
                decision["reasoning"].append("Moderate air quality detected (AQI > 50).")
                decision["confidence"] += 0.05

        # Influence 3: Anomaly response
        if temp_anomaly:
            if decision["action"] == "off":
                # If an anomaly is detected, and system is off, turn it on for investigation/correction
                decision["action"] = "auto" # Or "on" for a generic "on" state
            decision["reasoning"].append("Temperature anomaly detected.")
            decision["confidence"] += 0.3
            self.lstm_model.is_trained = False # Invalidate model, trigger retraining soon

        # Influence 4: Energy optimization influence (prioritize the decision for the very next hour)
        first_hour_optimal_decision = optimal_schedule[0] if optimal_schedule else None
        
        if first_hour_optimal_decision:
            if first_hour_optimal_decision["should_run"]:
                # If optimizer says run, reinforce decision or override 'off' if needed
                if decision["action"] == "off" and occupancy and current_temp not in range(20, 25): # Only if needed to move temp
                    decision["action"] = "auto" # Engage auto mode
                    decision["reasoning"].append("Energy optimization recommends engaging HVAC.")
                    decision["confidence"] += 0.1
                elif decision["action"] != "off": # Already planning to run, boost confidence slightly
                    decision["confidence"] = min(1.0, decision["confidence"] + 0.05)
            else: # Optimizer says NOT to run for energy savings
                if decision["action"] != "off" and decision["confidence"] > 0.4: # If we were planning to run
                    decision["confidence"] = max(0, decision["confidence"] - 0.2)
                    decision["reasoning"].append("Energy optimization suggests turning off or reducing activity.")
                    # If confidence drops low enough, consider overriding to off
                    if decision["confidence"] < 0.3:
                        decision["action"] = "off"
                        decision["reasoning"].append("HVAC turned OFF due to energy optimization and low confidence.")

        # Finalize confidence score (cap at 1.0)
        decision["confidence"] = min(1.0, decision["confidence"])
        
        # Add predictions and energy schedule to the decision for insights/dashboard
        decision["predictions"] = predicted_temps
        decision["energy_schedule"] = optimal_schedule[:3] # Show next 3 hours of optimized schedule

        logger.info(
            f"AI Decision for device {sensor_data.get('device_id', 'unknown')}: "
            f"Action: {decision['action'].upper()} (Conf: {decision['confidence']:.2f}) | "
            f"Target: {decision['target_temperature']}°C | Mode: {decision['mode']} | Fan: {decision['fan_speed']} | "
            f"Reasoning: [{'; '.join(decision['reasoning'])}]"
        )
        return decision