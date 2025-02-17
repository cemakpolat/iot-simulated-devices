import asyncio
import random
import logging
from bacpypes.app import BIPSimpleApplication, BIPForeignApplication
from bacpypes.local.device import LocalDeviceObject
from bacpypes.service.device import WhoIsIAmServices, DeviceCommunicationControlServices
from bacpypes.object import AnalogValueObject
from bacpypes.core import run_once, stop

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
class BACnetGateway:
    def __init__(self, device_id, ip_address, port):
        self.device = LocalDeviceObject(
            objectName="BACnetGateway",
            objectIdentifier=device_id,
            maxApduLengthAccepted=1476,
            segmentationSupported="segmentedBoth",
            vendorIdentifier=15,
        )
        self.app = BIPSimpleApplication(self.device, f"{ip_address}:{port}")
        self.app.add_capability(WhoIsIAmServices)
        self.app.add_capability(DeviceCommunicationControlServices)
        self.devices = {}

    def register_device(self, device_id, device_obj):
        self.devices[device_id] = device_obj

    async def respond_to_whois(self, low_limit=None, high_limit=None):
        for device_id, device_obj in self.devices.items():
            if low_limit is None or (low_limit <= device_id <= high_limit):
                device_obj.app.i_am(device_id=device_id)

    async def start(self):
        logging.info("Starting BACnet Gateway...")
        while True:
            await asyncio.sleep(0.1)  # Allow other tasks to run
            run_once()  # Run the BACpypes core event loop once

    async def stop(self):
        logging.info("Stopping BACnet Gateway...")
        stop()


class SimulatedBACnetDevice:
    def __init__(self, device_id, ip_address, port, bbmd_address, bbmd_ttl):
        self.device = LocalDeviceObject(
            objectName=f"Device_{device_id}",
            objectIdentifier=device_id,
            maxApduLengthAccepted=1476,
            segmentationSupported="segmentedBoth",
            vendorIdentifier=15,
        )
        self.app = BIPForeignApplication(
            self.device,
            f"{ip_address}:{port}",
            bbmdAddress=bbmd_address,
            bbmdTTL=bbmd_ttl,
        )
        self.temperature_sensor = AnalogValueObject(
            objectIdentifier=("analogValue", device_id),
            objectName="TemperatureSensor",
            presentValue=23.5,
            units="degreesCelsius",
        )
        self.app.add_object(self.temperature_sensor)

    async def update_temperature(self):
        while True:
            new_value = round(random.uniform(20.0, 30.0), 1)
            self.temperature_sensor.presentValue = new_value
            logging.info(f"Updated TemperatureSensor to: {new_value}")
            await asyncio.sleep(10)  # Update every 10 seconds

    async def start(self):
        logging.info(f"Starting Device {self.device.objectIdentifier}...")
        await self.update_temperature()

    async def stop(self):
        logging.info(f"Stopping Device {self.device.objectIdentifier}...")


class SimulationManager:
    def __init__(self, gateway_config, device_configs):
        self.gateway = BACnetGateway(**gateway_config)
        self.devices = [SimulatedBACnetDevice(**config) for config in device_configs]
        for device in self.devices:
            self.gateway.register_device(device.device.objectIdentifier, device)

    async def start(self):
        tasks = []
        # Start gateway task
        tasks.append(asyncio.create_task(self.gateway.start()))
        # Start device tasks
        for device in self.devices:
            tasks.append(asyncio.create_task(device.start()))
        return tasks

    async def stop(self, tasks):
        for device in self.devices:
            await device.stop()
        await self.gateway.stop()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    # Configuration
    gateway_config = {
        "device_id": 100,
        "ip_address": "0.0.0.0",
        "port": 47808,
    }
    device_configs = [
        {
            "device_id": 1,
            "ip_address": "0.0.0.0",
            "port": 47809,
            "bbmd_address": ("0.0.0.0", 47808),
            "bbmd_ttl": 1000,
        },
        {
            "device_id": 2,
            "ip_address": "0.0.0.0",
            "port": 47810,
            "bbmd_address": ("0.0.0.0", 47808),
            "bbmd_ttl": 1000,
        },
    ]

    # Initialize simulation manager
    manager = SimulationManager(gateway_config, device_configs)
    tasks = None
    try:
        tasks = await manager.start()
        print("Press Enter to stop the simulation...")
        await asyncio.Event().wait()  # Wait indefinitely until interrupted
    finally:
        if tasks:
            await manager.stop(tasks)


if __name__ == "__main__":
    asyncio.run(main())