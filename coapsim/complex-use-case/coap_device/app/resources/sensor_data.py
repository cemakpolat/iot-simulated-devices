# client/app/resources/sensor_data.py
import json
import aiocoap
import time
from aiocoap.resource import Resource
from sensors.temperature import AdvancedTemperatureSensor
from sensors.humidity import HumiditySensor
from sensors.air_quality import AirQualitySensor
from sensors.occupancy import OccupancySensor

class SensorDataResource(Resource):
    def __init__(self, device_id: str):
        super().__init__()
        self.device_id = device_id
        self.temp_sensor = AdvancedTemperatureSensor(device_id)
        self.humidity_sensor = HumiditySensor(device_id)
        self.air_quality_sensor = AirQualitySensor(device_id)
        self.occupancy_sensor = OccupancySensor(device_id)
        
    async def render_get(self, request):
        sensor_data = {
            "device_id": self.device_id,
            "timestamp": time.time(),
            "temperature": self.temp_sensor.read().__dict__,
            "humidity": self.humidity_sensor.read(),
            "air_quality": self.air_quality_sensor.read(),
            "occupancy": self.occupancy_sensor.read()
        }
        
        payload = json.dumps(sensor_data).encode('utf-8')
        return aiocoap.Message(payload=payload, content_format=50)  # JSON format
