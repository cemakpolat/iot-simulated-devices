import asyncio
import unittest

from bacnetsim.bacnet_async import BACnetDevice

import asyncio
import unittest
from unittest.mock import patch
from bacnetsim.bacnet_async import BACnetDevice


class TestBACnetSimulation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up a mock BACnet device for testing."""
        self.device = BACnetDevice(device_id=123, ip_address="127.0.0.1", port=47808)

    async def asyncTearDown(self):
        """Clean up after tests."""
        self.device.running = False  # Ensure that the device stops any active tasks
        await asyncio.sleep(0.1)  # Give some time for cleanup tasks

    async def test_device_initialization(self):
        """Test that the device and its objects are initialized correctly."""
        self.assertEqual(self.device.device.objectName, "SimulatedBACnetDevice123")
        self.assertEqual(self.device.device.objectIdentifier[1], 123)
        self.assertEqual(self.device.temperature_sensor.objectName, "TemperatureSensor")
        self.assertEqual(self.device.temperature_sensor.presentValue, 23.5)

    @patch("random.uniform")
    async def test_telemetry_update_with_cancellation(self, mock_random):
        """Test that the telemetry update function works as expected with task cancellation."""
        # Mock random values to ensure predictable results
        mock_random.side_effect = [25.0, 22.5, 24.0, 26.0]

        initial_value = self.device.temperature_sensor.presentValue

        async def stop_loop():
            await asyncio.sleep(1)  # Run for 1 second
            self.device.running = False  # Stop the device simulation

        # Start the telemetry update and the stop loop simultaneously
        await asyncio.gather(
            self.device.update_telemetry(),
            stop_loop()
        )

        new_value = self.device.temperature_sensor.presentValue

        # Ensure the value has changed and is within the expected range
        self.assertNotEqual(initial_value, new_value)
        self.assertGreaterEqual(new_value, 20.0)
        self.assertLessEqual(new_value, 30.0)

    @patch("random.uniform")
    async def test_multiple_updates_with_cancellation(self, mock_random):
        """Test multiple iterations of telemetry updates with task cancellation."""
        # Mock random values to ensure predictable results
        mock_random.side_effect = [25.0, 23.0, 24.5, 22.0]

        initial_value = self.device.temperature_sensor.presentValue

        # Create a task for the telemetry update
        telemetry_task = asyncio.create_task(self.device.update_telemetry())

        # Wait for a few seconds to allow multiple iterations to complete
        await asyncio.sleep(0.5)  # Allow multiple iterations to complete

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


if __name__ == "__main__":
    unittest.main()