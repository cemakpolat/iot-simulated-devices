# server/app/services/maintenance_service.py
"""Your MaintenanceService - keep exactly as provided"""
import logging
import time
import random 
from datetime import datetime, timedelta 
from typing import Dict, List, Any, Optional

from ..database.influxdb_client import InfluxDBClient
from ..services.notification_service import NotificationService 

logger = logging.getLogger(__name__)

class MaintenanceService:
    """
    Provides predictive maintenance capabilities for thermostat devices.
    Checks various metrics to identify potential issues and recommends maintenance actions.
    """
    def __init__(self, db_client: InfluxDBClient, notification_service: NotificationService):
        self.logger = logger
        self.db_client = db_client
        self.notification_service = notification_service
        self.maintenance_alerts: Dict[str, Dict[str, Any]] = {} 
        logger.info("MaintenanceService initialized.")

    async def check_maintenance_needs(self, device_status: dict) -> Optional[Dict[str, Any]]:
        device_id = device_status.get('device_id')
        if not device_id:
            logger.error("Device ID missing in device status for maintenance check. Cannot proceed.")
            return None

        uptime = device_status.get('uptime_seconds', 0)
        energy_consumption = device_status.get('energy_consumption', 0)
        current_temp = device_status.get('temperature', {}).get('value', None)
        
        maintenance_score = 0
        recommendations = set()
        
        # Rule 1: Uptime-based Routine Maintenance
        days_uptime = uptime / (24 * 3600)
        if days_uptime > 180:
            maintenance_score += 20
            recommendations.add(f"Routine maintenance: Device uptime {int(days_uptime)} days (over 180 days).")
        
        # Rule 2: High Energy Consumption Anomaly
        if energy_consumption > 0:
            historical_consumption_data = await self.db_client.get_energy_data(device_id, days=30)
            if historical_consumption_data:
                historical_consumptions = [entry['value'] for entry in historical_consumption_data if 'value' in entry and entry['value'] is not None]
                if historical_consumptions:
                    avg_consumption = sum(historical_consumptions) / len(historical_consumptions)
                    if avg_consumption > 0 and energy_consumption > avg_consumption * 1.3:
                        maintenance_score += 40
                        recommendations.add(f"High energy consumption ({energy_consumption:.2f} kWh) compared to average ({avg_consumption:.2f} kWh). Check filters/coils.")
        
        # Rule 3: Sensor Accuracy/Variance Check
        if current_temp is not None:
            temp_variance = await self.db_client.get_temperature_variance(device_id, hours=24)
            if temp_variance is not None and temp_variance > 2.0:
                maintenance_score += 35
                recommendations.add(f"High temperature variance ({temp_variance:.2f}°C) detected in last 24h. Calibrate sensors or check HVAC system.")
        
        # Rule 4: Last Maintenance Date
        last_maintenance_timestamp = device_status.get('last_maintenance', 0)
        if last_maintenance_timestamp and last_maintenance_timestamp > 0:
            last_maintenance_date = datetime.fromtimestamp(last_maintenance_timestamp)
            days_since_maintenance = (datetime.now() - last_maintenance_date).days
            if days_since_maintenance > 90:
                maintenance_score += 25
                recommendations.add(f"Last reported maintenance was {days_since_maintenance} days ago (over 90 days recommended interval).")
        else:
            maintenance_score += 5
            recommendations.add("Last maintenance date unknown. Recommend initial system check-up.")

        # Rule 5: Simulated Critical Internal Error
        if random.random() < 0.005:
            maintenance_score += 60
            recommendations.add("Critical internal system error detected. Requires immediate attention.")

        priority = self._get_priority_level(maintenance_score)
        
        result = {
            "device_id": device_id,
            "maintenance_score": maintenance_score,
            "priority": priority,
            "recommendations": list(recommendations),
            "estimated_cost": self._estimate_maintenance_cost(maintenance_score),
            "optimal_schedule_date": self._suggest_maintenance_date()
        }
        
        # Alerting Logic
        current_active_alert = self.maintenance_alerts.get(device_id)
        if maintenance_score > 30:
            if not current_active_alert or \
                current_active_alert['priority'] != priority or \
                current_active_alert['maintenance_score'] < maintenance_score:
                await self.db_client.store_maintenance_alert(result)
                self.maintenance_alerts[device_id] = result
                logger.warning(f"Maintenance alert triggered/updated for {device_id}: Priority '{priority}', Score {maintenance_score}")
                await self.notification_service.send_alert(
                    "maintenance_required", 
                    f"Thermostat {device_id} requires {priority} maintenance.", 
                    result
                )
        elif current_active_alert and maintenance_score <= 30:
            logger.info(f"Maintenance alert for {device_id} has cleared (score {maintenance_score}).")
            del self.maintenance_alerts[device_id]

        return result

    def _get_priority_level(self, score: int) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    def _estimate_maintenance_cost(self, score: int) -> Dict[str, float]:
        base_cost = 75.0
        parts_cost = max(0.0, (score - 50) * 2.0)
        labor_cost = max(50.0, score * 1.5)
        
        total = base_cost + parts_cost + labor_cost
        
        return {
            "service_call": round(base_cost, 2),
            "estimated_parts": round(parts_cost, 2),
            "estimated_labor": round(labor_cost, 2),
            "total_estimate": round(total, 2),
            "currency": "USD"
        }

    def _suggest_maintenance_date(self) -> str:
        suggested_date = datetime.now() + timedelta(days=7)
        
        while suggested_date.weekday() not in [1, 2, 3]: 
            suggested_date += timedelta(days=1)
        
        suggested_date = suggested_date.replace(hour=10, minute=0, second=0, microsecond=0)
        
        return suggested_date.isoformat()