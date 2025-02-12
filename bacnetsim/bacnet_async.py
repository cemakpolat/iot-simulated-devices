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
    # unittest.main()


# Test Suite
class TestBACnetSimulation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up a mock BACnet device for testing."""
        self.device = BACnetDevice(device_id=123, ip_address="127.0.0.1", port=47808)

    async def asyncTearDown(self):
        """Clean up after tests."""
        pass

    async def test_device_initialization(self):
        """Test that the device and its objects are initialized correctly."""
        self.assertEqual(self.device.device.objectName, "SimulatedBACnetDevice123")
        self.assertEqual(self.device.device.objectIdentifier[1], 123)
        self.assertEqual(self.device.temperature_sensor.objectName, "TemperatureSensor")
        self.assertEqual(self.device.temperature_sensor.presentValue, 23.5)

    async def test_telemetry_update_with_cancellation(self):
        """Test that the telemetry update function works as expected with task cancellation."""
        initial_value = self.device.temperature_sensor.presentValue

        async def stop_loop():
            await asyncio.sleep(1)  # Run for 3 seconds
            print("Stopping loop...")  # Debugging output

            self.device.running = False

        await asyncio.gather(
            self.device.update_telemetry(),
            stop_loop()
        )

        new_value = self.device.temperature_sensor.presentValue

        # Ensure the value has changed and is within the expected range
        self.assertNotEqual(initial_value, new_value)
        self.assertGreaterEqual(new_value, 20.0)
        self.assertLessEqual(new_value, 30.0)


    async def test_multiple_updates_with_cancellation(self):
        """Test multiple iterations of telemetry updates with task cancellation."""
        initial_value = self.device.temperature_sensor.presentValue

        # Create a task for the telemetry update
        telemetry_task = asyncio.create_task(self.device.update_telemetry())

        # Wait for a few seconds to allow multiple iterations to complete
        await asyncio.sleep(0.1)  # Allow multiple iterations to complete

        # Cancel the task
        telemetry_task.cancel()
        try:
            await telemetry_task  # Ensure the task is properly awaited after cancellation
        except asyncio.CancelledError:
            pass  # Task cancellation is expected behavior

        final_value = self.device.temperature_sensor.presentValue

        # Ensure the value has changed and is within the expected range
        self.assertNotEqual(initial_value, final_value)
        self.assertGreaterEqual(final_value, 20.0)
        self.assertLessEqual(final_value, 30.0)
