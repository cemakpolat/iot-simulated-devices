import asyncio
import os
from typing import Optional
from devices.data_generator import GeneratorFactory
from gateway.device_manager import DeviceManager


class GatewaySender:
    """Single gateway that sends data for all virtual devices"""

    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.slave_name: Optional[str] = None
        self.running = False
        self.sender_task: Optional[asyncio.Task] = None

    async def start(self) -> Optional[str]:
        """Start the gateway sender"""
        try:
            # Create PTY pair
            self.master_fd, self.slave_fd = os.openpty()
            self.slave_name = os.ttyname(self.slave_fd)
            self.running = True

            # Start the sender task
            self.sender_task = asyncio.create_task(self._sender_loop())

            print(f"[GatewaySender] Started on {self.slave_name}")
            return self.slave_name

        except Exception as e:
            print(f"[GatewaySender] Failed to start: {e}")
            await self.stop()
            return None

    async def stop(self):
        """Stop the gateway sender"""
        self.running = False

        if self.sender_task and not self.sender_task.done():
            self.sender_task.cancel()
            try:
                await self.sender_task
            except asyncio.CancelledError:
                pass

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except:
                pass
            self.master_fd = None

        if self.slave_fd is not None:
            try:
                os.close(self.slave_fd)
            except:
                pass
            self.slave_fd = None

        print("[GatewaySender] Stopped")

    async def _sender_loop(self):
        """Main sender loop - delays between devices"""
        try:
            with os.fdopen(self.master_fd, "wb", buffering=0) as sender:
                print("[GatewaySender] Sender loop started")

                while self.running:
                    try:
                        # Get devices ready to transmit
                        ready_devices = self.device_manager.get_ready_devices()

                        for device in ready_devices:
                            print(f"device:{device.name}")
                            await self._send_device_data(sender, device)
                            device.mark_transmitted()

                            await asyncio.sleep(2)  # 50ms delay between devices

                        # Sleep briefly before checking for ready devices again
                        await asyncio.sleep(10)

                    except Exception as e:
                        print(f"[GatewaySender] Error in sender loop: {e}")
                        await asyncio.sleep(1)

        except Exception as e:
            print(f"[GatewaySender] Sender loop error: {e}")

    async def _send_device_data(self, sender, device):
        """Send data for a specific device"""
        try:
            # Generate new data using the appropriate generator
            generator_class = GeneratorFactory.get_generator(device.eep_type)
            telegram = generator_class.generate(device.eep_type, device.base_telegram, device.sender_id)
            print(f"[SIMULATOR SENDS]: {telegram.hex().upper()}")

            # Send the telegram
            sender.write(telegram)
            sender.flush()

            print(f"[GatewaySender] {device.name} -> {telegram.hex()}")

        except Exception as e:
            print(f"[GatewaySender] Error sending data for {device.name}: {e}")

    def add_device(self, name: str, sender_id: bytes, eep_type, base_telegram: bytes, interval: float = 5.0) -> bool:
        """Add a device to the gateway"""
        return self.device_manager.add_device(name, sender_id, eep_type, base_telegram, interval)

    def remove_device(self, name: str) -> bool:
        """Remove a device from the gateway"""
        return self.device_manager.remove_device(name)

    def get_device_count(self) -> int:
        """Get number of managed devices"""
        return self.device_manager.get_device_count()

    def list_devices(self):
        """List all devices"""
        return self.device_manager.list_devices()