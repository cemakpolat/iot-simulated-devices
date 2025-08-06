# File: simulator/simulator_manager.py
from typing import Optional
from gateway.device_manager import DeviceManager
from gateway.gateway_sender import GatewaySender
from gateway.gateway_receiver import GatewayReceiver


class SimulatorManager:
    """Main simulator orchestrator"""

    def __init__(self, receiver_activated=False):
        # Create a shared device manager
        self.device_manager = DeviceManager()
        self.gateway_sender: Optional[GatewaySender] = None
        self.gateway_receiver: Optional[GatewayReceiver] = None
        self.gateway_receiver_is_activated = receiver_activated
        self.running = False

    async def start(self):
        """Start the simulator"""
        try:
            print("[SimulatorManager] Starting EnOcean Gateway Simulator...")

            # Create and start gateway sender
            self.gateway_sender = GatewaySender(device_manager=self.device_manager)
            print(f"[DEBUG] DeviceManager devices before start: {list(self.device_manager.devices.keys())}")

            gateway_port = await self.gateway_sender.start()
            print(f"gateway pott {gateway_port}")

            if not gateway_port:
                print("[SimulatorManager] Failed to start gateway sender")
                return False

            # Create and start gateway receiver
            # if self.gateway_receiver_is_activated:
            #     self.gateway_receiver = GatewayReceiver(device_manager=self.device_manager)
            #     await self.gateway_receiver.start(gateway_port)

            self.running = True
            print(f"[SimulatorManager] Simulator started successfully on {gateway_port}")
            return True

        except Exception as e:
            print(f"[SimulatorManager] Failed to start simulator: {e}")
            await self.stop()
            return False

    async def stop(self):
        """Stop the simulator"""
        print("[SimulatorManager] Stopping simulator...")
        self.running = False

        if self.gateway_receiver:
            await self.gateway_receiver.stop()

        if self.gateway_sender:
            await self.gateway_sender.stop()

        print("[SimulatorManager] Simulator stopped")

    def add_device(self, name: str, sender_id: bytes, eep_type, base_telegram: bytes, interval: float = 5.0) -> bool:
        """Add a device to the gateway"""
        if self.gateway_sender:
            return self.gateway_sender.add_device(name, sender_id, eep_type, base_telegram, interval)
        return False

    def remove_device(self, name: str) -> bool:
        """Remove a device from the gateway"""
        if self.gateway_sender:
            return self.gateway_sender.remove_device(name)
        return False

    def get_device_count(self) -> int:
        """Get number of devices"""
        if self.gateway_sender:
            return self.gateway_sender.get_device_count()
        return 0

    def list_devices(self):
        """List all devices"""
        if self.gateway_sender:
            return self.gateway_sender.list_devices()
        return []

    def is_running(self) -> bool:
        """Check if simulator is running"""
        return self.running
