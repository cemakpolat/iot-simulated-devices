# server/app/utils/validators.py
"""
Data validation utilities
"""
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Utility class for validating sensor data and control commands."""

    @staticmethod
    def validate_sensor_reading(data: dict, sensor_type: str) -> bool:
        """Validates a single sensor reading dictionary."""
        if not isinstance(data, dict):
            logger.warning(f"Invalid sensor data type for {sensor_type}: {type(data)}")
            return False

        if "value" not in data and "occupied" not in data and "aqi" not in data:
            logger.warning(f"Missing 'value', 'occupied', or 'aqi' in {sensor_type} data.")
            return False
        
        if "timestamp" not in data or not isinstance(data["timestamp"], (int, float)):
            logger.warning(f"Missing or invalid 'timestamp' in {sensor_type} data.")
            return False

        if sensor_type == "temperature":
            if not (-50 <= data.get("value", 0) <= 100): # Realistic temperature range
                logger.warning(f"Temperature value {data.get('value')} out of expected range.")
                return False
        elif sensor_type == "humidity":
            if not (0 <= data.get("value", 0) <= 100): # Humidity percentage
                logger.warning(f"Humidity value {data.get('value')} out of expected range.")
                return False
        elif sensor_type == "air_quality":
            if not (0 <= data.get("aqi", 0) <= 500): # AQI range
                logger.warning(f"AQI value {data.get('aqi')} out of expected range.")
                return False
        elif sensor_type == "occupancy":
            if not isinstance(data.get("occupied"), bool):
                logger.warning(f"Occupied status must be boolean for occupancy sensor.")
                return False
        
        return True

    @staticmethod
    def validate_all_sensor_data(full_data: dict) -> bool:
        """Validates the combined sensor data payload."""
        if not isinstance(full_data, dict):
            logger.error("Full sensor data must be a dictionary.")
            return False
        
        required_keys = ["device_id", "timestamp", "temperature", "humidity"]
        for key in required_keys:
            if key not in full_data:
                logger.error(f"Missing required key in full sensor data: {key}")
                return False
        
        if not DataValidator.validate_sensor_reading(full_data.get("temperature", {}), "temperature"):
            logger.error("Temperature data failed validation.")
            return False
        if not DataValidator.validate_sensor_reading(full_data.get("humidity", {}), "humidity"):
            logger.error("Humidity data failed validation.")
            return False
        if "air_quality" in full_data and not DataValidator.validate_sensor_reading(full_data.get("air_quality", {}), "air_quality"):
            logger.error("Air quality data failed validation.")
            return False
        if "occupancy" in full_data and not DataValidator.validate_sensor_reading(full_data.get("occupancy", {}), "occupancy"):
            logger.error("Occupancy data failed validation.")
            return False

        return True

    @staticmethod
    def validate_control_command(command: dict) -> bool:
        """Validates an incoming control command."""
        if not isinstance(command, dict):
            logger.warning("Control command must be a dictionary.")
            return False

        if "hvac_state" in command and command["hvac_state"] not in ["on", "off", "heating", "cooling", "fan_only"]:
            logger.warning(f"Invalid hvac_state: {command['hvac_state']}")
            return False
        
        if "target_temperature" in command:
            temp = float(command["target_temperature"])
            if not (15 <= temp <= 30): # Reasonable target temp range
                logger.warning(f"Target temperature {temp} out of expected range (15-30).")
                return False
                
        if "mode" in command and command["mode"] not in ["auto", "heat", "cool", "off"]:
            logger.warning(f"Invalid mode: {command['mode']}")
            return False
            
        if "fan_speed" in command and command["fan_speed"] not in ["low", "medium", "high", "auto"]:
            logger.warning(f"Invalid fan_speed: {command['fan_speed']}")
            return False
            
        return True