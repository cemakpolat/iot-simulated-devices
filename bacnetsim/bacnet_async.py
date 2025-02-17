# pip install bacpypes3
import asyncio
import random
import logging
from bacpypes3.app import Application
from bacpypes3.local.device import DeviceObject
from bacpypes3.object import AnalogValueObject

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


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
            objectName="TemperatureSensor",
            presentValue=23.5,
            units="degreesCelsius",
        )

        self.humidity = AnalogValueObject(
            objectIdentifier=("analogValue", device_id + 1),
            objectName="HumiditySensor",
            presentValue=50.0,
            units="percentRelativeHumidity",
        )

        self.co2 = AnalogValueObject(
            objectIdentifier=("analogValue", device_id + 2),
            objectName="CO2Sensor",
            presentValue=400.0,
            units="partsPerMillion",
        )

        self.pressure = AnalogValueObject(
            objectIdentifier=("analogValue", device_id + 3),
            objectName="PressureSensor",
            presentValue=101325.0,  # Standard atmospheric pressure
            units="pascals",
        )

        # Register objects
        self.app.add_object(self.temperature_sensor)
        self.app.add_object(self.humidity)
        self.app.add_object(self.co2)
        self.app.add_object(self.pressure)

    async def update_telemetry(self):
        while self.running:
            try:

                self.temperature_sensor.presentValue = round(random.uniform(15.0, 35.0), 1)
                self.humidity.presentValue = round(random.uniform(30.0, 90.0), 1)
                self.co2.presentValue = round(random.uniform(400, 2000), 1)
                self.pressure.presentValue = round(random.uniform(95000, 105000), 1)

                logging.info(f"[{self.device.objectName}] Temperature: {self.temperature_sensor.presentValue} °C")
                logging.info(f"[{self.device.objectName}] Humidity: {self.humidity.presentValue} %")
                logging.info(f"[{self.device.objectName}] CO2: {self.co2.presentValue} ppm")
                logging.info(f"[{self.device.objectName}] Pressure: {self.pressure.presentValue} Pa")

            except Exception as e:
                logging.error(f"Error updating telemetry for {self.device.objectName}: {e}")

            await asyncio.sleep(10)  # Update every 10 seconds


async def main():
    devices_config = [
        {"device_id": 600, "ip_address": "0.0.0.0", "port": 47808},
        {"device_id": 601, "ip_address": "0.0.0.0", "port": 47809},
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