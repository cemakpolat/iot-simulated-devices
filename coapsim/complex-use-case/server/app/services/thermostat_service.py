# server/app/services/thermostat_service.py
import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from ..models.ensemble_model import EnsemblePredictor
from ..database.influxdb_client import InfluxDBClient
from ..coap.client import EnhancedCoAPClient
from ..services.prediction_service import PredictionService 
from ..services.maintenance_service import MaintenanceService 
from ..services.notification_service import NotificationService 
from ..database.redis_client import RedisClient

logger = logging.getLogger(__name__)

class ThermostatControlService:
    """
    Manages the core control loop for the smart thermostat.
    """
    def __init__(self, ensemble_model_instance: EnsemblePredictor, db_client: InfluxDBClient, 
                    coap_client: EnhancedCoAPClient, notification_service: NotificationService,
                    prediction_service: PredictionService, maintenance_service: MaintenanceService, 
                    redis_client: RedisClient):
        self.logger = logger
        self.ensemble_model = ensemble_model_instance
        self.db_client = db_client
        self.coap_client = coap_client
        self.notification_service = notification_service
        self.prediction_service = prediction_service  
        self.maintenance_service = maintenance_service 
        self.redis_client = redis_client
        self.decision_history = []
        self._last_processed_sensor_data: Optional[Dict[str, Any]] = None
        self._last_predictions: Optional[List[float]] = None
        
        logger.info("ThermostatControlService initialized with all dependencies.")

    def get_last_processed_data(self) -> Optional[Dict[str, Any]]:
        return self._last_processed_sensor_data

    def get_last_predictions(self) -> Optional[List[float]]:
        return self._last_predictions


    async def process_control_cycle(self):
        """Execute a single cycle of thermostat control"""
        try:
            # 1. Get current sensor data and device status
            sensor_data = await self.coap_client.get_all_sensor_data()
            device_status = await self.coap_client.get_device_status()

            if not sensor_data or not device_status:
                self.logger.warning("Failed to get complete data from device")
                return
            
            # Merge device status into sensor_data
            current_device_data = {**sensor_data, **device_status}
            self._last_processed_sensor_data = current_device_data
            logger.debug(f"Current device data received: Temp={current_device_data.get('temperature', {}).get('value')}°C")

            # Cache in Redis
            await self.redis_client.set(
                f"latest_sensor_data:{current_device_data.get('device_id', 'unknown')}", 
                json.dumps(current_device_data), 
                ex=30
            )

            # 2. Get historical data for ML models
            historical_data = await self.db_client.get_recent_data(
                hours=self.prediction_service.lstm_predictor.sequence_length + 24
            )
            if historical_data.empty or len(historical_data) < self.prediction_service.lstm_predictor.sequence_length:
                self.logger.warning("Insufficient historical data for ML models")

            # 3. Store current data in InfluxDB
            await self.db_client.store_sensor_data(current_device_data) 
            logger.debug(f"Data stored in InfluxDB for {current_device_data.get('device_id')}")

            # 4. Make AI decision using ensemble model
            decision = self.ensemble_model.make_decision(current_device_data, historical_data)
            self._last_predictions = decision.get("predictions")

            # 5. Execute the AI decision
            success = await self.execute_decision(decision)

            # 6. Log and store decision
            self.log_decision(current_device_data, decision)
            self.decision_history.append({
                "timestamp": datetime.now(),
                "sensor_data": current_device_data, 
                "decision": decision,
                "command_success": success
            })
            
            # Manage decision history size
            if len(self.decision_history) > 1000:
                self.decision_history = self.decision_history[-500:]

        except Exception as e:
            self.logger.error(f"Error in thermostat control cycle: {e}", exc_info=True)
            await self.notification_service.send_alert(
                "system_failure", 
                f"Critical error in thermostat control loop: {e}", 
                {"component": "ThermostatControlService", 
                 "device_id": sensor_data.get('device_id', 'unknown_device') if sensor_data else 'unknown_device'}
            )

    async def execute_decision(self, decision: dict) -> bool:
        """Execute the AI-determined HVAC decision"""
        control_command = {
            "hvac_state": decision.get("action", "off"),
            "target_temperature": decision.get("target_temperature", 22.0),
            "fan_speed": decision.get("fan_speed", "auto"),
            "mode": decision.get("mode", "auto")
        }
        
        success = await self.coap_client.send_control_command(control_command)
        
        if success:
            self.logger.info(f"CoAP command executed successfully: {control_command}")
        else:
            self.logger.error(f"Failed to execute CoAP command: {control_command}")
            await self.notification_service.send_alert(
                "device_command_failure", 
                f"Failed to send HVAC command to device: {control_command.get('hvac_state', 'N/A')}", 
                {"device_id": self._last_processed_sensor_data.get('device_id', 'unknown_device') if self._last_processed_sensor_data else 'unknown_device', 
                 "command": control_command}
            )
        return success
    
    def log_decision(self, sensor_data: dict, decision: dict):
        """Log the AI decision and sensor data"""
        current_temp = sensor_data.get('temperature', {}).get('value', 'N/A')
        current_hvac_state = sensor_data.get('hvac_state', 'N/A')
        
        action = decision.get('action', 'N/A')
        target_temp = decision.get('target_temperature', 'N/A')
        confidence = decision.get('confidence', 0.0)
        reasoning = '; '.join(decision.get('reasoning', []))
        
        self.logger.info(
            f"[{sensor_data.get('device_id', 'Unknown Device')}] "
            f"🌡️ Current: {current_temp}°C | Action: {action.upper()} | Target: {target_temp}°C "
            f"(Prev HVAC: {current_hvac_state} -> Recommended: {action.upper()}) | "
            f"Confidence: {confidence:.2f} - Reasoning: [{reasoning}]"
        )
