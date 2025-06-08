import logging
import time
import random 
from datetime import datetime, timedelta 
from typing import Dict, List, Any, Optional

from database.influxdb_client import InfluxDBClient
from services.notification_service import NotificationService 

logger = logging.getLogger(__name__)

class MaintenanceService:
    """
    Provides predictive maintenance capabilities for thermostat devices.
    Checks various metrics to identify potential issues and recommends maintenance actions.
    """
    def __init__(self, db_client: InfluxDBClient, notification_service: NotificationService):
        """
        Initializes the MaintenanceService with injected database client and notification service.
        """
        self.logger = logger
        self.db_client = db_client
        self.notification_service = notification_service
        # Dictionary to keep track of active maintenance alerts per device, to avoid duplicate notifications
        self.maintenance_alerts: Dict[str, Dict[str, Any]] = {} 
        logger.info("MaintenanceService initialized.")

    async def check_maintenance_needs(self, device_status: dict) -> Optional[Dict[str, Any]]:
        """
        Evaluates the current status of a device against various criteria to determine
        if maintenance is needed and its priority.
        :param device_status: A dictionary containing the device's current status (including merged sensor data).
        :return: A dictionary with maintenance recommendations and estimated costs, or None if device_id is missing.
        """
        device_id = device_status.get('device_id')
        if not device_id:
            logger.error("Device ID missing in device status for maintenance check. Cannot proceed.")
            return None

        uptime = device_status.get('uptime_seconds', 0)
        energy_consumption = device_status.get('energy_consumption', 0) # Current energy consumption from device_status
        current_temp = device_status.get('temperature', {}).get('value', None) # Current temp from sensor data
        
        maintenance_score = 0 # Higher score means higher maintenance priority
        recommendations = set() # Use a set to avoid duplicate recommendations
        
        # --- Rule 1: Uptime-based Routine Maintenance (e.g., every 6 months) ---
        days_uptime = uptime / (24 * 3600)
        if days_uptime > 180: # If device has been active for more than 180 days (approx. 6 months)
            maintenance_score += 20 # Low priority for routine check
            recommendations.add(f"Routine maintenance: Device uptime {int(days_uptime)} days (over 180 days).")
        
        # --- Rule 2: High Energy Consumption Anomaly ---
        # Compare current energy consumption with historical average to detect inefficiency
        if energy_consumption > 0: # Only check if current consumption is positive
            historical_consumption_data = await self.db_client.get_energy_data(device_id, days=30)
            if historical_consumption_data:
                # Extract 'value' from each dict and filter out None/invalid values
                historical_consumptions = [entry['value'] for entry in historical_consumption_data if 'value' in entry and entry['value'] is not None]
                if historical_consumptions:
                    avg_consumption = sum(historical_consumptions) / len(historical_consumptions)
                    if avg_consumption > 0 and energy_consumption > avg_consumption * 1.3: # If current consumption is 30% higher than average
                        maintenance_score += 40 # Medium priority
                        recommendations.add(f"High energy consumption ({energy_consumption:.2f} kWh) compared to average ({avg_consumption:.2f} kWh). Check filters/coils.")
                        # An alert will be sent if the total maintenance score crosses a threshold.
                else:
                    logger.debug(f"No historical energy consumption data found for device {device_id} to compare against.")
            else:
                logger.debug(f"No historical energy consumption data retrieved from DB for device {device_id}.")
        
        # --- Rule 3: Sensor Accuracy/Variance Check ---
        # High temperature variance might indicate a faulty sensor or inefficient HVAC operation (e.g., thermostat struggling to maintain temp)
        if current_temp is not None:
            temp_variance = await self.db_client.get_temperature_variance(device_id, hours=24)
            if temp_variance is not None and temp_variance > 2.0: # If variance is high (e.g., more than 2 degrees fluctuation)
                maintenance_score += 35 # Medium priority
                recommendations.add(f"High temperature variance ({temp_variance:.2f}°C) detected in last 24h. Calibrate sensors or check HVAC system.")
        else:
            logger.warning(f"Current temperature not available for device {device_id} to check variance.")


        # --- Rule 4: Last Maintenance Date ---
        # Suggest maintenance if too long since last service
        last_maintenance_timestamp = device_status.get('last_maintenance', 0) # Unix timestamp from device status
        if last_maintenance_timestamp and last_maintenance_timestamp > 0: # Ensure timestamp is valid
            last_maintenance_date = datetime.fromtimestamp(last_maintenance_timestamp)
            days_since_maintenance = (datetime.now() - last_maintenance_date).days
            if days_since_maintenance > 90: # If more than 3 months since last maintenance
                maintenance_score += 25 # Low-medium priority
                recommendations.add(f"Last reported maintenance was {days_since_maintenance} days ago (over 90 days recommended interval).")
        else:
            # If no last_maintenance date is provided, assume it's new or not tracked.
            # Could trigger an initial check or just track from now.
            maintenance_score += 5
            recommendations.add("Last maintenance date unknown. Recommend initial system check-up.")

        # --- Rule 5: Simulated Critical Internal Error ---
        # For demonstration, a small random chance of a critical error
        if random.random() < 0.005: # 0.5% chance
            maintenance_score += 60 # Significant impact
            recommendations.add("Critical internal system error detected. Requires immediate attention.")

        # Determine the overall priority level based on the total score
        priority = self._get_priority_level(maintenance_score)
        
        result = {
            "device_id": device_id,
            "maintenance_score": maintenance_score,
            "priority": priority,
            "recommendations": list(recommendations), # Convert set back to list
            "estimated_cost": self._estimate_maintenance_cost(maintenance_score),
            "optimal_schedule_date": self._suggest_maintenance_date()
        }
        
        # --- Alerting Logic ---
        current_active_alert = self.maintenance_alerts.get(device_id)
        if maintenance_score > 30: # Threshold for triggering a maintenance alert
            if not current_active_alert or \
                current_active_alert['priority'] != priority or \
                current_active_alert['maintenance_score'] < maintenance_score:
                # Trigger/update alert if it's new, severity changed, or score increased
                await self.db_client.store_maintenance_alert(result) # Store alert in DB
                self.maintenance_alerts[device_id] = result # Update in-memory cache
                logger.warning(f"Maintenance alert triggered/updated for {device_id}: Priority '{priority}', Score {maintenance_score}")
                await self.notification_service.send_alert(
                    "maintenance_required", 
                    f"Thermostat {device_id} requires {priority} maintenance.", 
                    result
                )
        elif current_active_alert and maintenance_score <= 30: # Clear alert if conditions improve
            logger.info(f"Maintenance alert for {device_id} has cleared (score {maintenance_score}).")
            del self.maintenance_alerts[device_id] # Remove from active alerts

        return result

    def _get_priority_level(self, score: int) -> str:
        """Assigns a human-readable priority level based on the maintenance score."""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    def _estimate_maintenance_cost(self, score: int) -> Dict[str, float]:
        """Estimates the cost of maintenance based on the score."""
        base_cost = 75.0  # Base service call fee
        parts_cost = max(0.0, (score - 50) * 2.0)  # Additional parts cost if score is higher
        labor_cost = max(50.0, score * 1.5)  # Labor cost increases with complexity (score)
        
        total = base_cost + parts_cost + labor_cost
        
        return {
            "service_call": round(base_cost, 2),
            "estimated_parts": round(parts_cost, 2),
            "estimated_labor": round(labor_cost, 2),
            "total_estimate": round(total, 2),
            "currency": "USD"
        }

    def _suggest_maintenance_date(self) -> str:
        """Suggests an optimal future date/time for maintenance (e.g., next Tuesday-Thursday, 10 AM-2 PM)."""
        suggested_date = datetime.now() + timedelta(days=7) # Start with next week
        
        # Find the next Tuesday (weekday 1), Wednesday (weekday 2), or Thursday (weekday 3)
        while suggested_date.weekday() not in [1, 2, 3]: 
            suggested_date += timedelta(days=1)
        
        # Set to optimal time window (e.g., 10 AM)
        suggested_date = suggested_date.replace(hour=10, minute=0, second=0, microsecond=0)
        
        return suggested_date.isoformat()