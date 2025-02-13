# pip install bacpypes3
import asyncio
import random
import logging
from bacpypes3.app import Application
from bacpypes3.local.device import DeviceObject
from bacpypes3.object import AnalogValueObject

import unittest
from unittest.mock import AsyncMock, patch

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class BACnetDevice:
    def __init__(self, device_id, ip_address, port):
        self.running = True
        self.device = DeviceObject(
            objectName=f"SimulatedBACnetDevice{device_id}",
            objectIdentifier=device_id,
            maxApduLengthAccepted=1476,
            segmentationSupported="segmentedBoth",
            vendorIdentifier=15,
        )
        self.app = Application(self.device, f"{ip_address}/{port}")
        self.temperature_sensor = AnalogValueObject(
            objectIdentifier=("analogValue", device_id),
            objectName=f"TemperatureSensor",
            presentValue=23.5,
            units="degreesCelsius",
        )
        self.app.add_object(self.temperature_sensor)

    async def update_telemetry(self):
        while self.running:
            try:
                new_value = round(random.uniform(20.0, 30.0), 1)
                self.temperature_sensor.presentValue = new_value
                logging.info(f"Updated TemperatureSensor value for {self.device.objectName} to: {new_value}")
            except Exception as e:
                logging.error(f"Error updating telemetry for {self.device.objectName}: {e}")
            await asyncio.sleep(5)


async def main():
    devices_config = [
        {"device_id": 599, "ip_address": "0.0.0.0", "port": 47809},
        {"device_id": 600, "ip_address": "0.0.0.0", "port": 47808},
    ]

    tasks = []
    for config in devices_config:
        device = BACnetDevice(config["device_id"], config["ip_address"], config["port"])
        tasks.append(asyncio.create_task(device.update_telemetry()))

    logging.info("Press Ctrl+C to stop the simulation...")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Simulation stopped by user.")
        # Uncomment the following line to run tests
