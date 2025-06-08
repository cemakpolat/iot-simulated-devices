import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Imports for components passed as dependencies
from models.ensemble_model import EnsemblePredictor
from database.influxdb_client import InfluxDBClient
from coap.client import EnhancedCoAPClient
from services.prediction_service import PredictionService 
from services.maintenance_service import MaintenanceService 
from services.notification_service import NotificationService 

logger = logging.getLogger(__name__)

class ThermostatControlService:
    """
    Manages the core control loop for the smart thermostat.
    It orchestrates data fetching, AI decision making, command execution,
    and data storage.
    """
    def __init__(self, ensemble_model_instance: EnsemblePredictor, db_client: InfluxDBClient, 
                    coap_client: EnhancedCoAPClient, notification_service: NotificationService,
                    prediction_service: PredictionService, maintenance_service: MaintenanceService):
        """
        Initializes the ThermostatControlService with all its required dependencies.
        :param ensemble_model_instance: An instance of EnsemblePredictor for AI decisions.
        :param db_client: An instance of InfluxDBClient for data persistence.
        :param coap_client: An instance of EnhancedCoAPClient for device communication.
        :param notification_service: An instance of NotificationService for alerts.
        :param prediction_service: An instance of PredictionService (for access to its states).
        :param maintenance_service: An instance of MaintenanceService (for access to its states).
        """
        self.logger = logger
        self.ensemble_model = ensemble_model_instance
        self.db_client = db_client
        self.coap_client = coap_client
        self.notification_service = notification_service
        self.prediction_service = prediction_service  
        self.maintenance_service = maintenance_service 
        self.decision_history = [] # Stores recent control decisions for logging/debugging
        self._last_processed_sensor_data: Optional[Dict[str, Any]] = None # Cache for dashboard/WS
        self._last_predictions: Optional[List[float]] = None # Cache for dashboard/WS
        
        logger.info("ThermostatControlService initialized with all dependencies.")

    def get_last_processed_data(self) -> Optional[Dict[str, Any]]:
        """
        Returns the last comprehensive sensor data and device status processed by the control cycle.
        Useful for external components like WebSockets or REST APIs.
        """
        return self._last_processed_sensor_data

    def get_last_predictions(self) -> Optional[List[float]]:
        """
        Returns the last temperature predictions made by the ensemble model.
        Useful for external components like WebSockets or REST APIs.
        """
        return self._last_predictions

    async def process_control_cycle(self):
        """
        Executes a single cycle of thermostat control:
        1. Fetches sensor data and device status from the CoAP device.
        2. Retrieves historical data from InfluxDB.
        3. Stores the latest sensor data and status in InfluxDB.
        4. Uses the EnsemblePredictor to make an HVAC control decision.
        5. Executes the decision by sending a CoAP command to the device.
        6. Logs the decision and stores it in history.
        """
        try:
            # 1. Get current sensor data and device status from the thermostat device
            sensor_data = await self.coap_client.get_all_sensor_data()
            device_status = await self.coap_client.get_device_status()

            if not sensor_data or not device_status:
                self.logger.warning("Failed to get complete data from device (sensor_data or device_status missing). Skipping control cycle.")
                # Consider adding a specific alert if connectivity issues persist for a defined duration
                # await self.notification_service.send_alert("connectivity_issue", "Failed to retrieve full device data.", {"device_id": "smart-thermostat-01"})
                return
            
            # Merge device status into sensor_data for unified processing and storage
            # This ensures the `store_sensor_data` in InfluxDB client can save all relevant fields.
            current_device_data = {**sensor_data, **device_status} # Merge dictionaries
            self._last_processed_sensor_data = current_device_data # Cache for external access
            logger.debug(f"Current device data received: Temp={current_device_data.get('temperature', {}).get('value')}°C, HVAC={current_device_data.get('hvac_state', 'N/A')}")

            # 2. Get historical data for ML models from InfluxDB
            # The amount of historical data needed depends on the LSTM's `sequence_length`
            # and how much data the anomaly detector needs for training.
            historical_data = await self.db_client.get_recent_data(hours=self.prediction_service.lstm_predictor.sequence_length + 24) # e.g., 24h + 24h for sequence
            if historical_data.empty or len(historical_data) < self.prediction_service.lstm_predictor.sequence_length:
                self.logger.warning("Insufficient historical data for ML models. Some features might be limited or fallback used.")
                # The ML models should have internal fallbacks or handle empty data gracefully.

            # 3. Store current sensor data and device status in InfluxDB
            await self.db_client.store_sensor_data(current_device_data) 
            logger.debug(f"Sensor and device status data stored in InfluxDB for {current_device_data.get('device_id')}.")

            # 4. Make AI decision using the ensemble model
            decision = self.ensemble_model.make_decision(current_device_data, historical_data)
            self._last_predictions = decision.get("predictions") # Cache predictions for external access

            # 5. Execute the AI decision on the device
            success = await self.execute_decision(decision)

            # 6. Log and store the decision for historical analysis and debugging
            self.log_decision(current_device_data, decision)
            self.decision_history.append({
                "timestamp": datetime.now(),
                "sensor_data": current_device_data, 
                "decision": decision,
                "command_success": success
            })
            
            # Manage decision history size to prevent excessive memory usage
            if len(self.decision_history) > 1000: # Keep up to 1000 recent decisions
                self.decision_history = self.decision_history[-500:] # Discard oldest half

        except Exception as e:
            self.logger.error(f"Error in thermostat control cycle: {e}", exc_info=True)
            # Send a critical alert if the control cycle itself encounters a significant error
            await self.notification_service.send_alert(
                "system_failure", 
                f"Critical error in thermostat control loop: {e}", 
                {"component": "ThermostatControlService", "device_id": sensor_data.get('device_id', 'unknown_device') if sensor_data else 'unknown_device'}
            )

    async def execute_decision(self, decision: dict) -> bool:
        """
        Executes the AI-determined HVAC decision by sending a CoAP control command to the device.
        :param decision: The decision dictionary generated by the ensemble model.
        :return: True if the command was successfully sent, False otherwise.
        """
        control_command = {
            "hvac_state": decision.get("action", "off"),
            "target_temperature": decision.get("target_temperature", 22.0),
            "fan_speed": decision.get("fan_speed", "auto"),
            "mode": decision.get("mode", "auto")
        }
        
        # Send the command via the CoAP client
        success = await self.coap_client.send_control_command(control_command)
        
        if success:
            self.logger.info(f"CoAP command executed successfully on device: {control_command}")
        else:
            self.logger.error(f"Failed to execute CoAP command on device: {control_command}")
            # Send an alert if the command fails to reach or be processed by the device
            await self.notification_service.send_alert(
                "device_command_failure", 
                f"Failed to send HVAC command to device: {control_command.get('hvac_state', 'N/A')}", 
                {"device_id": self._last_processed_sensor_data.get('device_id', 'unknown_device') if self._last_processed_sensor_data else 'unknown_device', "command": control_command}
            )
        return success
    
    def log_decision(self, sensor_data: dict, decision: dict):
        """Logs the AI decision and relevant sensor data for monitoring and debugging."""
        current_temp = sensor_data.get('temperature', {}).get('value', 'N/A')
        current_hvac_state = sensor_data.get('hvac_state', 'N/A') # Current state from device
        
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
        # Future: Log this decision to a structured database (e.g., PostgreSQL or InfluxDB)
        # for retrospective analysis of AI performance.