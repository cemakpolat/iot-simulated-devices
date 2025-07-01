# server/app/models/ensemble_model.py
"""Your EnsemblePredictor - keep exactly as provided"""
import numpy as np
import pandas as pd
import logging 
from datetime import datetime, timedelta 
import random 

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
        self.lstm_model = lstm_model
        self.anomaly_detector = anomaly_detector
        self.energy_optimizer = energy_optimizer
        logger.info("EnsemblePredictor initialized with injected models.")

    def make_decision(self, sensor_data: dict, historical_data: pd.DataFrame) -> dict:
        """Make comprehensive HVAC control decision"""
        current_temp = sensor_data.get('temperature', {}).get('value')
        occupancy = sensor_data.get('occupancy', {}).get('occupied')
        air_quality_aqi = sensor_data.get('air_quality', {}).get('aqi')

        if current_temp is None or occupancy is None or air_quality_aqi is None:
            logger.error("Missing critical sensor data for decision making")
            return {
                "action": "off", "target_temperature": 22.0, "mode": "auto", "fan_speed": "auto",
                "reasoning": ["Missing critical sensor data."], "confidence": 0.0,
                "predictions": [], "energy_schedule": []
            }

        # 1. Get Temperature Predictions
        predicted_temps = self.lstm_model.predict(historical_data, hours_ahead=6)
        if predicted_temps is None or not predicted_temps:
            predicted_temps = [current_temp] * 6
            logger.warning("LSTM temperature prediction failed, using current temperature as fallback")

        # 2. Detect Anomalies
        temp_anomaly = False
        if 'temperature' in sensor_data and 'humidity' in sensor_data:
            current_features_df = pd.DataFrame([{
                'temperature': sensor_data['temperature']['value'], 
                'humidity': sensor_data['humidity']['value']
            }])
            anomaly_prediction = self.anomaly_detector.predict(current_features_df, feature_columns=['temperature', 'humidity'])
            if anomaly_prediction.size > 0:
                temp_anomaly = anomaly_prediction[0] == -1
                if temp_anomaly:
                    logger.warning(f"Temperature anomaly detected: {current_temp}°C")

        # 3. Energy Optimization
        occupancy_schedule = [occupancy] * len(predicted_temps)  
        optimal_schedule = self.energy_optimizer.optimize_schedule(
            current_temp, 22.0, predicted_temps, occupancy_schedule
        )
        if not optimal_schedule:
            logger.warning("Energy optimization failed to produce a schedule")
            optimal_schedule = [{"hour": (datetime.now().hour + i) % 24, "should_run": False, "intensity": 0.0} for i in range(len(predicted_temps))]

        # 4. Ensemble Decision Logic
        decision = {
            "action": "off",
            "target_temperature": 22.0,
            "mode": "auto",
            "fan_speed": "auto",
            "reasoning": [],
            "confidence": 0.0
        }

        # Temperature-based control
        if occupancy:
            if current_temp > 25:
                decision["action"] = "cool"
                decision["target_temperature"] = 22.0
                decision["reasoning"].append("High temperature with occupancy detected.")
                decision["confidence"] += 0.4
            elif current_temp < 20:
                decision["action"] = "heat"
                decision["target_temperature"] = 22.0
                decision["reasoning"].append("Low temperature with occupancy detected.")
                decision["confidence"] += 0.4
        else:
            if current_temp > 28:
                decision["action"] = "cool"
                decision["target_temperature"] = 26.0
                decision["reasoning"].append("Extreme high temperature (unoccupied).")
                decision["confidence"] += 0.1
            elif current_temp < 15:
                decision["action"] = "heat"
                decision["target_temperature"] = 18.0
                decision["reasoning"].append("Extreme low temperature (unoccupied).")
                decision["confidence"] += 0.1
            else:
                decision["action"] = "off"
                decision["reasoning"].append("System off (unoccupied, within tolerance).")

        # Air Quality consideration
        if air_quality_aqi > 100:
            decision["fan_speed"] = "high"
            decision["reasoning"].append("Poor air quality detected (AQI > 100).")
            decision["confidence"] += 0.2
        elif air_quality_aqi > 50 and decision["fan_speed"] == "auto":
                decision["fan_speed"] = "medium"
                decision["reasoning"].append("Moderate air quality detected (AQI > 50).")
                decision["confidence"] += 0.05

        # Anomaly response
        if temp_anomaly:
            if decision["action"] == "off":
                decision["action"] = "auto"
            decision["reasoning"].append("Temperature anomaly detected.")
            decision["confidence"] += 0.3
            self.lstm_model.is_trained = False

        # Energy optimization influence
        first_hour_optimal_decision = optimal_schedule[0] if optimal_schedule else None
        
        if first_hour_optimal_decision:
            if first_hour_optimal_decision["should_run"]:
                if decision["action"] == "off" and occupancy and current_temp not in range(20, 25):
                    decision["action"] = "auto"
                    decision["reasoning"].append("Energy optimization recommends engaging HVAC.")
                    decision["confidence"] += 0.1
                elif decision["action"] != "off":
                    decision["confidence"] = min(1.0, decision["confidence"] + 0.05)
            else:
                if decision["action"] != "off" and decision["confidence"] > 0.4:
                    decision["confidence"] = max(0, decision["confidence"] - 0.2)
                    decision["reasoning"].append("Energy optimization suggests reducing activity.")
                    if decision["confidence"] < 0.3:
                        decision["action"] = "off"
                        decision["reasoning"].append("HVAC turned OFF due to energy optimization.")

        decision["confidence"] = min(1.0, decision["confidence"])
        decision["predictions"] = predicted_temps
        decision["energy_schedule"] = optimal_schedule[:3]

        logger.info(
            f"AI Decision: Action: {decision['action'].upper()} (Conf: {decision['confidence']:.2f}) | "
            f"Target: {decision['target_temperature']}°C | Reasoning: [{'; '.join(decision['reasoning'])}]"
        )
        return decision
