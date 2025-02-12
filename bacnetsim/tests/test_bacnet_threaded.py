import unittest
from unittest.mock import MagicMock, patch
import logging

from bacnetsim.bacnet_thread import BACnetDevice, DeviceManager, TelemetryTask

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TestBACnetSimulation(unittest.TestCase):

    def setUp(self):
        """Set up a BACnet device for testing."""
        self.device_id = 123
        self.ip_address = "127.0.0.1"
        self.port = 47808
        self.device = BACnetDevice(self.device_id, self.ip_address, self.port)

    def test_device_initialization(self):
        """Test that the device and its objects are initialized correctly."""
        self.assertEqual(self.device.device.objectName, "SimulatedBACnetDevice123")
        self.assertEqual(self.device.device.objectIdentifier[1], 123)
        self.assertEqual(self.device.temperature_sensor.objectName, "TemperatureSensor")
        self.assertEqual(self.device.temperature_sensor.presentValue, 23.5)


class TestTelemetryTask(unittest.TestCase):

    def setUp(self):
        """Set up a BACnet device for testing."""
        self.device_id = 123
        self.ip_address = "127.0.0.1"
        self.port = 47808
        self.device = BACnetDevice(self.device_id, self.ip_address, self.port)

    @patch("bacpypes.task.RecurringTask.install_task")
    def test_telemetry_task(self, mock_install_task):
        """Test that the telemetry task updates the sensor value correctly."""
        initial_value = self.device.temperature_sensor.presentValue

        # Mock the RecurringTask's install_task method to avoid running the actual event loop
        mock_install_task.return_value = None

        # Manually trigger the process_task method of the telemetry task
        self.device.telemetry_task.process_task()

        new_value = self.device.temperature_sensor.presentValue

        # Ensure the value has changed and is within the expected range
        self.assertNotEqual(initial_value, new_value)
        self.assertGreaterEqual(new_value, 20.0)
        self.assertLessEqual(new_value, 30.0)

    @patch("random.uniform", return_value=25.0)
    @patch("logging.info")
    def test_telemetry_task_updates_sensor(self, mock_log, mock_random):
        device = MagicMock()
        device.device.objectIdentifier = 599
        task = TelemetryTask(5.0, device)

        task.process_task()

        self.assertAlmostEqual(device.temperature_sensor.presentValue, 25.0)
        mock_log.assert_called_with("[Device 599] Updated TemperatureSensor value to: 25.0")


class TestDeviceManager(unittest.TestCase):
    def setUp(self):
        self.manager = DeviceManager()

    @patch("bacnetsim.main_thread.BACnetDevice")
    def test_add_device(self, mock_device):
        device = self.manager.add_device(599, "0.0.0.0", 47810)

        self.assertEqual(len(self.manager.devices), 1)
        mock_device.assert_called_once_with(599, "0.0.0.0", 47810)
        self.assertEqual(device, mock_device.return_value)

    @patch("threading.Thread")
    def test_start_devices(self, mock_thread):
        mock_device = MagicMock()
        self.manager.devices.append(mock_device)

        self.manager.start_devices()

        mock_thread.assert_called_once_with(target=mock_device.start)
        mock_thread.return_value.start.assert_called_once()

    @patch.object(BACnetDevice, "stop")  # Mock `stop` to track calls
    @patch.object(BACnetDevice, "start", return_value=None)  # Mock `start` to prevent blocking
    def test_stop_devices(self, mock_start, mock_stop):
        """Test that stop_devices properly stops all devices."""
        self.manager.start_devices()  # Start (mocked, no real threads)
        self.manager.stop_devices()  # Stop should be called on all devices

        # Ensure stop() is called once per device
        self.assertEqual(mock_stop.call_count, len(self.manager.devices))
