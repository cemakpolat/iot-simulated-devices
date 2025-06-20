# app/repositories/timeseries_repository.py
"""Time series data repository for sensor data."""

import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ..infrastructure.database.influxdb import InfluxDBClient
from ..core.exceptions import DatabaseError


class TimeseriesRepository:
    """Repository for time series data operations using InfluxDB."""
    
    def __init__(self, influx_client: InfluxDBClient):
        self.influx_client = influx_client
    
    async def store_sensor_data(self, device_id: str, sensor_data: Dict[str, Any]):
        """Store sensor data in InfluxDB."""
        try:
            await self.influx_client.store_sensor_data(device_id, sensor_data)
        except Exception as e:
            raise DatabaseError(f"Failed to store sensor data: {str(e)}")
    
    async def get_recent_data(self, device_id: str = None, hours: int = 24) -> pd.DataFrame:
        """Get recent sensor data as DataFrame."""
        try:
            return await self.influx_client.get_recent_data(device_id, hours)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve recent data: {str(e)}")
    
    async def get_temperature_data(self, device_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get temperature data for a specific time range."""
        try:
            # This would implement a specific InfluxDB query for temperature data
            query = f'''
            from(bucket: "{self.influx_client.config["bucket"]}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => 
                    r._measurement == "sensor_data" and 
                    r.device_id == "{device_id}" and
                    r.sensor_type == "temperature" and
                    r._field == "value")
                |> sort(columns: ["_time"])
            '''
            
            tables = self.influx_client.query_api.query(query, org=self.influx_client.config["org"])
            
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        "time": record["_time"].isoformat(),
                        "value": record["_value"],
                        "device_id": record["device_id"]
                    })
            
            return results
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve temperature data: {str(e)}")
    
    async def get_energy_data(self, device_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get energy consumption data."""
        try:
            query = f'''
            from(bucket: "{self.influx_client.config["bucket"]}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => 
                    r._measurement == "device_status" and 
                    r.device_id == "{device_id}" and
                    r._field == "energy_consumption")
                |> sort(columns: ["_time"])
            '''
            
            tables = self.influx_client.query_api.query(query, org=self.influx_client.config["org"])
            
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        "time": record["_time"].isoformat(),
                        "value": record["_value"],
                        "device_id": record["device_id"]
                    })
            
            return results
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve energy data: {str(e)}")
    
    async def get_temperature_variance(self, device_id: str, hours: int = 24) -> Optional[float]:
        """Calculate temperature variance for a device over a period."""
        try:
            query = f'''
            from(bucket: "{self.influx_client.config["bucket"]}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => 
                    r._measurement == "sensor_data" and 
                    r.device_id == "{device_id}" and 
                    r.sensor_type == "temperature" and
                    r._field == "value")
                |> keep(columns: ["_time", "_value"])
            '''
            
            tables = self.influx_client.query_api.query(query, org=self.influx_client.config["org"])
            
            temperatures = []
            for table in tables:
                for record in table.records:
                    temperatures.append(record["_value"])
            
            if temperatures:
                df = pd.Series(temperatures)
                variance = df.var()
                if pd.isna(variance):
                    variance = 0.0
                return float(variance)
            else:
                return None
                
        except Exception as e:
            raise DatabaseError(f"Failed to calculate temperature variance: {str(e)}")
    
    async def store_maintenance_alert(self, alert_data: Dict[str, Any]):
        """Store maintenance alert in InfluxDB."""
        try:
            from influxdb_client import Point
            
            point = Point("maintenance_alert") \
                .tag("device_id", alert_data['device_id']) \
                .tag("priority", alert_data['priority']) \
                .field("score", int(alert_data['maintenance_score'])) \
                .field("estimated_total_cost", float(alert_data['estimated_cost']['total_estimate'])) \
                .field("recommendations_count", len(alert_data['recommendations'])) \
                .time(datetime.now())
            
            self.influx_client.write_api.write(
                bucket=self.influx_client.config["bucket"], 
                record=point, 
                org=self.influx_client.config["org"]
            )
            
        except Exception as e:
            raise DatabaseError(f"Failed to store maintenance alert: {str(e)}")
    
    async def get_device_statistics(self, device_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive device statistics."""
        try:
            # Get temperature statistics
            temp_query = f'''
            from(bucket: "{self.influx_client.config["bucket"]}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => 
                    r._measurement == "sensor_data" and 
                    r.device_id == "{device_id}" and 
                    r.sensor_type == "temperature" and
                    r._field == "value")
                |> mean()
            '''
            
            # Get humidity statistics
            humidity_query = f'''
            from(bucket: "{self.influx_client.config["bucket"]}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => 
                    r._measurement == "sensor_data" and 
                    r.device_id == "{device_id}" and 
                    r.sensor_type == "humidity" and
                    r._field == "value")
                |> mean()
            '''
            
            # Execute queries and collect results
            # This is simplified - you would need to properly handle the query results
            
            stats = {
                "device_id": device_id,
                "period_days": days,
                "average_temperature": 22.0,  # Placeholder
                "average_humidity": 45.0,     # Placeholder
                "data_points": 1000,          # Placeholder
                "uptime_percentage": 95.5,    # Placeholder
                "last_updated": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            raise DatabaseError(f"Failed to get device statistics: {str(e)}")
    
    async def cleanup_old_data(self, days_to_keep: int = 365):
        """Clean up old sensor data beyond retention period."""
        try:
            # This would implement data cleanup logic
            # InfluxDB typically handles this through retention policies
            pass
        except Exception as e:
            raise DatabaseError(f"Failed to cleanup old data: {str(e)}")

