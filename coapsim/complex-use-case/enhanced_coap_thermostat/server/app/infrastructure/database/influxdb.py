from ...core.config import get_settings
from ...core.exceptions import DatabaseError
from ...utils import logger
import datetime
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd     
from influxdb_client import InfluxDBClient as InfluxClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import ApiException
from influxdb_client.domain.write_precision import WritePrecision
from influxdb_client.domain.write_api import SYNCHRONOUS
from influxdb_client.domain.point import Point


logger = logger.getLogger(__name__)
settings = get_settings()
class InfluxDBClient:
    """InfluxDB client for time series data with enhanced error handling."""
    def __init__(self):
        self.client = None
        self.write_api = None
        self.query_api = None
        self._initialized = False
        self.config = settings.influxdb_config

    async def initialize(self):
        """Initialize InfluxDB client."""
        try:
            self.client = InfluxClient(**self.config)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            await self._test_connection()
            
            self._initialized = True
            logger.info("InfluxDB client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {e}")
            raise DatabaseError(f"InfluxDB initialization failed: {str(e)}")

    async def _test_connection(self):
        """Test InfluxDB connection."""
        try:
            # Simple ping query
            query = f'from(bucket: "{self.config["bucket"]}") |> range(start: -1m) |> limit(n:1)'
            list(self.query_api.query(query, org=self.config["org"]))
        except ApiException as e:
            if e.status == 404:
                logger.warning("InfluxDB bucket not found, but connection is working")
            else:
                raise

    async def store_sensor_data(self, device_id: str, sensor_data: Dict[str, Any]):
        """Store sensor data with improved error handling."""
        if not self._initialized:
            raise DatabaseError("InfluxDB client not initialized")
        
        try:
            points = self._create_sensor_points(device_id, sensor_data)
            
            if points:
                self.write_api.write(
                    bucket=self.config["bucket"], 
                    record=points, 
                    org=self.config["org"]
                )
                logger.debug(f"Stored {len(points)} sensor data points for device {device_id}")
            else:
                logger.warning(f"No valid sensor data points to store for device {device_id}")
                
        except Exception as e:
            logger.error(f"Error storing sensor data for device {device_id}: {e}")
            raise DatabaseError(f"Failed to store sensor data: {str(e)}")

    def _create_sensor_points(self, device_id: str, sensor_data: Dict[str, Any]) -> List[Point]:
        """Create InfluxDB points from sensor data."""
        points = []
        timestamp = datetime.now()
        
        # Temperature data
        if 'temperature' in sensor_data:
            temp_data = sensor_data['temperature']
            if isinstance(temp_data, dict) and 'value' in temp_data:
                points.append(
                    Point("sensor_data")
                    .tag("device_id", device_id)
                    .tag("sensor_type", "temperature")
                    .field("value", float(temp_data['value']))
                    .field("unit", temp_data.get('unit', 'celsius'))
                    .time(timestamp)
                )
        
        # Humidity data
        if 'humidity' in sensor_data:
            humidity_data = sensor_data['humidity']
            if isinstance(humidity_data, dict) and 'value' in humidity_data:
                points.append(
                    Point("sensor_data")
                    .tag("device_id", device_id)
                    .tag("sensor_type", "humidity")
                    .field("value", float(humidity_data['value']))
                    .field("unit", humidity_data.get('unit', 'percent'))
                    .time(timestamp)
                )
        
        # Air quality data
        if 'air_quality' in sensor_data:
            air_data = sensor_data['air_quality']
            if isinstance(air_data, dict):
                point = Point("sensor_data") \
                    .tag("device_id", device_id) \
                    .tag("sensor_type", "air_quality") \
                    .time(timestamp)
                
                for key, value in air_data.items():
                    if isinstance(value, (int, float)):
                        point.field(key, float(value))
                    elif isinstance(value, str):
                        point.field(key, value)
                
                points.append(point)
        
        # Occupancy data
        if 'occupancy' in sensor_data:
            occupancy_data = sensor_data['occupancy']
            if isinstance(occupancy_data, dict) and 'occupied' in occupancy_data:
                points.append(
                    Point("sensor_data")
                    .tag("device_id", device_id)
                    .tag("sensor_type", "occupancy")
                    .field("value", 1.0 if occupancy_data['occupied'] else 0.0)
                    .field("confidence", float(occupancy_data.get('confidence', 0.0)))
                    .time(timestamp)
                )
        
        return points

    async def get_recent_data(self, device_id: str = None, hours: int = 24) -> pd.DataFrame:
        """Get recent sensor data as DataFrame."""
        if not self._initialized:
            raise DatabaseError("InfluxDB client not initialized")
        
        try:
            device_filter = f'and r.device_id == "{device_id}"' if device_id else ''
            
            query = f'''
            from(bucket: "{self.config["bucket"]}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => 
                    r._measurement == "sensor_data" and 
                    r._field == "value" and
                    (r.sensor_type == "temperature" or 
                    r.sensor_type == "humidity" or 
                    r.sensor_type == "occupancy") {device_filter})
                |> pivot(rowKey:["_time", "device_id"], columnKey: ["sensor_type"], valueColumn: "_value")
                |> keep(columns: ["_time", "device_id", "temperature", "humidity", "occupancy"])
                |> sort(columns: ["_time"])
            '''
            
            result = self.query_api.query_data_frame(query=query, org=self.config["org"])
            
            if not result.empty:
                # Process the data
                result['timestamp'] = pd.to_datetime(result['_time']).astype(int) // 10**9
                
                # Ensure numeric types
                for col in ['temperature', 'humidity']:
                    if col in result.columns:
                        result[col] = pd.to_numeric(result[col], errors='coerce')
                        result[col] = result[col].fillna(result[col].mean())
                    else:
                        result[col] = 0.0
                
                if 'occupancy' in result.columns:
                    result['occupancy'] = pd.to_numeric(result['occupancy'], errors='coerce').fillna(0).astype(int)
                else:
                    result['occupancy'] = 0
                
                return result[['timestamp', 'temperature', 'humidity', 'occupancy']].dropna()
            
            logger.info(f"No recent data found for the last {hours} hours")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error querying recent data: {e}")
            raise DatabaseError(f"Failed to query recent data: {str(e)}")

    async def close(self):
        """Close InfluxDB client."""
        if self.client:
            self.client.close()
            logger.info("InfluxDB client closed")
