from unittest.mock import MagicMock, patch, call
import logging

# Import the classes to be tested
from bacnetsim.bacnet_gateway import BACnetGateway, SimulatedBACnetDevice, SimulationManager

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

#
import unittest
from unittest.mock import MagicMock, patch
import threading
import time

class TestBACnetGateway(unittest.TestCase):
    def setUp(self):
        """Set up a BACnetGateway instance for testing."""
        self.device_id = 100
        self.ip_address = "0.0.0.0"
        self.port = 0
        self.gateway = BACnetGateway(self.device_id, self.ip_address, self.port)

    def test_register_device(self):
        mock_device = MagicMock()
        self.gateway.register_device(1, mock_device)
        self.assertIn(1, self.gateway.devices)
        self.assertEqual(self.gateway.devices[1], mock_device)

    @patch("bacnetsim.bacnet_gateway.run")
    def test_start_gateway(self, mock_run):
        with patch("bacnetsim.bacnet_gateway.stop") as mock_stop:
            thread = threading.Thread(target=self.gateway.start, daemon=True)
            thread.start()
            time.sleep(1)
            mock_run.assert_called_once()
            self.gateway.stop()
            thread.join()
            mock_stop.assert_called_once()


class TestSimulatedBACnetDevice(unittest.TestCase):

    def setUp(self):
        self.device = SimulatedBACnetDevice(
            device_id=1, ip_address="127.0.0.1", port=47809,
            bbmd_address=("127.0.0.1", 47808), bbmd_ttl=1000
        )

    def test_update_temperature(self):
        initial_value = self.device.temperature_sensor.presentValue
        self.device.update_temperature()
        new_value = self.device.temperature_sensor.presentValue
        self.assertNotEqual(initial_value, new_value)
        self.assertTrue(20.0 <= new_value <= 30.0)


class TestSimulationManager(unittest.TestCase):

    # we assign the port numbers to 0, so that the OS can assign the port number dynamically.
    # Otherwise we receive "already assigned" error.
    def setUp(self):
        gateway_config = {
            "device_id": 100,
            "ip_address": "127.0.0.1",
            "port": 0,
        }
        device_configs = [
            {
                "device_id": 1,
                "ip_address": "127.0.0.1",
                "port": 0,
                "bbmd_address": ("127.0.0.1", 0),
                "bbmd_ttl": 1000,
            }
        ]
        self.manager = SimulationManager(gateway_config, device_configs)

    @patch("threading.Thread")
    def test_start(self, mock_thread):
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        mock_thread_instance.start = MagicMock()

        threads = self.manager.start()
        self.assertEqual(len(threads), 2)  # Gateway thread + 1 device thread

        expected_calls = [
            call(target=self.manager.gateway.start, daemon=True),
            call(target=self.manager.devices[0].start, daemon=True),
        ]
        mock_thread.assert_has_calls(expected_calls, any_order=True)

    @patch.object(SimulatedBACnetDevice, "stop")
    @patch.object(BACnetGateway, "stop")
    def test_stop(self, mock_gateway_stop, mock_device_stop):
        """Test that the SimulationManager stops threads correctly."""
        mock_thread = MagicMock()
        self.manager.stop([mock_thread])
        mock_device_stop.assert_called_once()
        mock_gateway_stop.assert_called_once()
        mock_thread.join.assert_called_once()


if __name__ == "__main__":
    unittest.main()
