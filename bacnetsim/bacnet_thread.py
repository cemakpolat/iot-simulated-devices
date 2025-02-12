import warnings
warnings.filterwarnings("ignore", message="no signal handlers for child threads")

import threading
import random
import logging
import time

from bacpypes.app import BIPSimpleApplication
from bacpypes.local.device import LocalDeviceObject
from bacpypes.service.device import WhoIsIAmServices
from bacpypes.object import AnalogValueObject
from bacpypes.core import run, stop, deferred
from bacpypes.task import RecurringTask

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelemetryTask(RecurringTask):
    def __init__(self, interval, device):
        super().__init__(interval)
        self.device = device

    def process_task(self):
        try:
            # Simulate temperature changes
            new_value = round(random.uniform(20.0, 30.0), 1)
            self.device.temperature_sensor.presentValue = new_value
            logging.info(
                f"[Device {self.device.device.objectIdentifier}] Updated TemperatureSensor value to: {new_value}")
            time.sleep(self.taskInterval)
        except Exception as e:
            logging.error(f"[Device {self.device.device.objectIdentifier}] Error updating telemetry: {e}",
                          exc_info=True)


class BACnetDevice:
    def __init__(self, device_id, ip_address, port):
        # Create the local device object
        self.device = LocalDeviceObject(
            objectName=f"SimulatedBACnetDevice{device_id}",
            objectIdentifier=device_id,
            maxApduLengthAccepted=1476,
            segmentationSupported="segmentedBoth",
            vendorIdentifier=15,
        )
        # Application instance
        self.app = BIPSimpleApplication(self.device, f"{ip_address}:{port}")
        # Add services
        self.app.add_capability(WhoIsIAmServices)
        # Add objects
        self.temperature_sensor = AnalogValueObject(
            objectIdentifier=("analogValue", device_id),
            objectName=f"TemperatureSensor",
            presentValue=23.5,
            units="degreesCelsius",
        )
        self.app.add_object(self.temperature_sensor)
        # Create and schedule telemetry update task
        self.telemetry_task = TelemetryTask(5.0, self)  # Run every 5 seconds
        deferred(self.telemetry_task.install_task)

    def start(self):
        logging.info(f"[Device {self.device.objectIdentifier}] Simulated BACnet device running...")
        run()

    def stop(self):
        logging.info(f"[Device {self.device.objectIdentifier}] Stopping BACnet device simulation...")
        stop()


class DeviceManager:
    def __init__(self):
        self.devices = []
        self.threads = []

    def add_device(self, device_id, ip_address, port):
        device = BACnetDevice(device_id, ip_address, port)
        self.devices.append(device)
        return device

    def start_devices(self):
        for device in self.devices:
            simulation_thread = threading.Thread(target=device.start)
            self.threads.append(simulation_thread)
            simulation_thread.start()

    def stop_devices(self):
        # Stop all devices
        for device in self.devices:
            device.stop()
        # Join all threads
        for thread in self.threads:
            thread.join()


def main():
    manager = None #
    try:
        # Configuration for multiple devices
        devices_config = [
            {"device_id": 599, "ip_address": "0.0.0.0", "port": 47809},
            {"device_id": 600, "ip_address": "0.0.0.0", "port": 47808},
            # Add more devices as needed
        ]

        # Initialize the device manager
        manager = DeviceManager()

        # Add and configure devices
        for config in devices_config:
            manager.add_device(config["device_id"], config["ip_address"], config["port"])

        # Start all devices
        manager.start_devices()

        # Wait for user input to stop the simulation
        input("Press Enter to stop the simulation...\n")

    except Exception as err:
        logging.error(f"Unexpected error occurred: {err}", exc_info=True)
    finally:
        # Stop all devices and join threads
        if manager is not None:
            manager.stop_devices()
            logging.info("All devices stopped successfully.")
        else:
            logging.warning("No devices were started; nothing to stop.")


if __name__ == "__main__":
    main()
