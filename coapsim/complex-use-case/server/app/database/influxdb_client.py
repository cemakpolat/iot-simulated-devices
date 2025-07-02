# """InfluxDB client for time-series sensor data"""

from influxdb_client import InfluxDBClient as InfluxClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
from datetime import datetime, timedelta
import os 
import logging 
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class InfluxDBClient:
    def __init__(self):
        try:
            self.url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
            self.token = os.getenv("INFLUXDB_TOKEN", "admin-token")
            self.org = os.getenv("INFLUXDB_ORG", "thermostat-org")
            self.bucket = os.getenv("INFLUXDB_BUCKET", "thermostat-data")

            # Initialize client only if essential credentials are provided
            if self.token and self.org:
                self.client = InfluxClient(url=self.url, token=self.token, org=self.org)
                # Synchronous write API is suitable for low-to-medium throughput
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                logger.info(f"InfluxDBClient initialized for {self.url}, org: {self.org}, bucket: {self.bucket}")
            else:
                logger.warning("INFLUXDB_TOKEN or INFLUXDB_ORG not set. InfluxDB client will not be active.")
                self.client = None # Mark client as not active/ready
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDBClient: {e}", exc_info=True)
            self.client = None # Mark client as not active

    async def store_sensor_data(self, sensor_data: dict):
        """
        Stores combined sensor and device status data in InfluxDB.
        Data points are grouped by measurement and device_id.
        """
        if not self.client:
            logger.error("InfluxDB client not active. Cannot store sensor data.")
            return

        try:
            points = []
            timestamp = datetime.now() # Use server's timestamp for consistency
            device_id = sensor_data.get('device_id', 'unknown_device')
            
            # --- Store sensor data under "sensor_data" measurement ---
            # All sensor types will now use the "value" field for their primary reading.

            temp_data = sensor_data.get('temperature', {})
            if 'value' in temp_data:
                points.append(
                    Point("sensor_data")
                    .tag("device_id", device_id)
                    .tag("sensor_type", "temperature")
                    .field("value", float(temp_data['value'])) # Use 'value' field
                    .field("unit", temp_data.get('unit', 'celsius'))
                    .field("accuracy", float(temp_data.get('accuracy', 0.1)))
                    .time(timestamp)
                )
            
            humidity_data = sensor_data.get('humidity', {})
            if 'value' in humidity_data:
                points.append(
                    Point("sensor_data")
                    .tag("device_id", device_id)
                    .tag("sensor_type", "humidity")
                    .field("value", float(humidity_data['value'])) # Use 'value' field
                    .field("unit", humidity_data.get('unit', 'percent'))
                    .field("status", humidity_data.get('status', 'normal'))
                    .time(timestamp)
                )
            
            air_data = sensor_data.get('air_quality', {})
            if air_data:
                points.append(
                    Point("sensor_data")
                    .tag("device_id", device_id)
                    .tag("sensor_type", "air_quality")
                    # For air quality, the main value might be AQI or a specific pollutant
                    # For simplicity, we'll keep multiple fields for air_quality,
                    # as it's not part of the pivot for ML model currently.
                    .field("pm2_5", float(air_data.get('pm2_5', 0)))
                    .field("pm10", float(air_data.get('pm10', 0)))
                    .field("co2", float(air_data.get('co2', 0)))
                    .field("aqi", int(air_data.get('aqi', 0)))
                    .field("quality", air_data.get('quality', 'unknown'))
                    .time(timestamp)
                )
            
            occupancy_data = sensor_data.get('occupancy', {})
            if 'occupied' in occupancy_data:
                points.append(
                    Point("sensor_data")
                    .tag("device_id", device_id)
                    .tag("sensor_type", "occupancy")
                    .field("value", 1.0 if bool(occupancy_data['occupied']) else 0.0) # Store as float (1.0 or 0.0)
                    .field("confidence", float(occupancy_data.get('confidence', 0))) # Keep other metadata fields
                    .field("motion_detected", bool(occupancy_data.get('motion_detected', False)))
                    .time(timestamp)
                )
            
            # --- Store device status data under "device_status" measurement ---
            status_fields = {
                "uptime_seconds": sensor_data.get('uptime_seconds'), 
                "hvac_state": sensor_data.get('hvac_state'),
                "target_temperature": sensor_data.get('target_temperature'),
                "energy_consumption": sensor_data.get('energy_consumption'),
                "firmware_version": sensor_data.get('firmware_version'),
                "last_maintenance": sensor_data.get('last_maintenance')
            }
            filtered_status_fields = {}
            for k, v in status_fields.items():
                if v is not None:
                    if k in ["uptime_seconds", "target_temperature", "energy_consumption", "last_maintenance"]:
                        filtered_status_fields[k] = float(v)
                    else:
                        filtered_status_fields[k] = str(v)
            
            if filtered_status_fields:
                point = Point("device_status") \
                    .tag("device_id", device_id) \
                    .time(timestamp)
                for field_name, field_value in filtered_status_fields.items():
                    point.field(field_name, field_value)
                points.append(point)

            if points:
                self.write_api.write(bucket=self.bucket, record=points, org=self.org)
                logger.debug(f"Stored {len(points)} data points for device {device_id} in InfluxDB.")
            else:
                logger.warning(f"No valid points to store for device {device_id}.")
            
        except Exception as e:
            logger.error(f"Error storing data in InfluxDB for device {device_id}: {e}", exc_info=True)
    
    async def get_recent_data(self, hours: int = 24) -> pd.DataFrame:
        """
        Retrieves recent sensor data (temperature, humidity, occupancy) from InfluxDB
        and formats it into a Pandas DataFrame suitable for ML model training.
        """
        if not self.client:
            logger.error("InfluxDB client not active. Cannot query recent data.")
            return pd.DataFrame()

        try:
            # Flux query to fetch sensor data, pivot it to wide format, and select specific columns
            # Now that all relevant sensor data is under the 'value' field, _value will be populated
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => 
                    r._measurement == "sensor_data" and 
                    r._field == "value" and // Filter specifically for the 'value' field
                    (r.sensor_type == "temperature" or 
                     r.sensor_type == "humidity" or 
                     r.sensor_type == "occupancy"))
                |> pivot(rowKey:["_time", "device_id"], columnKey: ["sensor_type"], valueColumn: "_value")
                |> keep(columns: ["_time", "device_id", "temperature", "humidity", "occupancy"])
                |> sort(columns: ["_time"])
            '''
            
            result = self.query_api.query_data_frame(query=query, org=self.org)
            
            if not result.empty:
                # Convert '_time' column to Unix timestamp (seconds since epoch)
                result['timestamp'] = pd.to_datetime(result['_time']).astype(int) // 10**9
                
                # Ensure numerical types and handle potential missing values
                for col in ['temperature', 'humidity']:
                    if col in result.columns:
                        result[col] = pd.to_numeric(result[col], errors='coerce')
                        result[col] = result[col].fillna(result[col].mean() if not result[col].empty else 0.0) 
                    else:
                        result[col] = 0.0 # Add column with default value if missing from query result

                if 'occupancy' in result.columns:
                    # 'occupancy' is now stored as float (1.0 or 0.0), so convert to int (1 or 0)
                    result['occupancy'] = pd.to_numeric(result['occupancy'], errors='coerce').fillna(0).astype(int)
                else:
                    result['occupancy'] = 0 # Add if missing

                return result[['timestamp', 'temperature', 'humidity', 'occupancy']].dropna()
            
            logger.info(f"No recent data found in InfluxDB for the last {hours} hours.")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error querying recent data from InfluxDB: {e}", exc_info=True)
            return pd.DataFrame()

    async def store_maintenance_alert(self, alert_data: dict):
        """Stores a maintenance alert record in InfluxDB."""
        if not self.client:
            logger.error("InfluxDB client not active. Cannot store maintenance alert.")
            return

        try:
            point = Point("maintenance_alert") \
                .tag("device_id", alert_data['device_id']) \
                .tag("priority", alert_data['priority']) \
                .field("score", int(alert_data['maintenance_score'])) \
                .field("estimated_total_cost", float(alert_data['estimated_cost']['total_estimate'])) \
                .field("recommendations_count", len(alert_data['recommendations'])) \
                .time(datetime.now()) # Use current server time for alert timestamp
            
            self.write_api.write(bucket=self.bucket, record=point, org=self.org)
            logger.info(f"Stored maintenance alert for device {alert_data['device_id']}.")
            
        except Exception as e:
            logger.error(f"Error storing maintenance alert in InfluxDB: {e}", exc_info=True)

    async def get_energy_data(self, device_id: str, days: int = 7) -> List[Dict]:
        """Retrieves historical energy consumption data for a device."""
        if not self.client:
            logger.error("InfluxDB client not active. Cannot get energy data.")
            return []

        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => r._measurement == "device_status" and r.device_id == "{device_id}")
                |> filter(fn: (r) => r._field == "energy_consumption")
                |> yield(name: "energy_consumption")
            '''
            
            tables = self.query_api.query(query, org=self.org)
            
            results = []
            for table in tables:
                for record in table.records:
                    # FIX: Access FluxRecord fields using square bracket notation
                    results.append({
                        "time": record["_time"].isoformat(),
                        "value": record["_value"],
                        "device_id": record["device_id"]
                    })
            logger.debug(f"Retrieved {len(results)} energy data points for device {device_id}.")
            return results
        except Exception as e:
            logger.error(f"Error getting energy data from InfluxDB for device {device_id}: {e}", exc_info=True)
            return []

    async def get_temperature_variance(self, device_id: str, hours: int = 24) -> float:
        """Calculates temperature variance for a device over a period."""
        if not self.client:
            logger.error("InfluxDB client not active. Cannot calculate temperature variance.")
            return None

        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "sensor_data" and r.device_id == "{device_id}" and r.sensor_type == "temperature")
                |> filter(fn: (r) => r._field == "value")
                |> keep(columns: ["_time", "_value"])
                |> yield(name: "temperature_values")
            '''
            
            tables = self.query_api.query(query, org=self.org)
            
            temperatures = []
            for table in tables:
                for record in table.records:
                    # FIX: Access FluxRecord fields using square bracket notation
                    temperatures.append(record["_value"])
            
            if temperatures:
                df = pd.Series(temperatures)
                variance = df.var() # pandas .var() computes sample variance
                if pd.isna(variance): # Handle cases with constant temperature (variance is NaN for single value or all same values)
                    variance = 0.0
                logger.debug(f"Temperature variance for {device_id} over {hours}h: {variance:.2f}")
                return float(variance)
            else:
                logger.info(f"No temperature data found for variance calculation for device {device_id} in {hours} hours.")
                return None
        except Exception as e:
            logger.error(f"Error calculating temperature variance for device {device_id}: {e}", exc_info=True)
            return None