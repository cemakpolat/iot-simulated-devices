# main.py - Enhanced EnOcean Simulator with Device Registry Support
import asyncio
import signal
import sys
import json
from pathlib import Path
from simulator.simulator_manager import SimulatorManager
from simulator_devices import SIMULATOR_DEVICES, save_gateway_config



class EnOceanSimulator:
    def __init__(self, gateway_config_file="devices.json"):
        self.simulator = SimulatorManager(receiver_activated=True)
        self.running = False
        self.gateway_config_file = gateway_config_file
        self.device_registry = {}

    async def setup_devices_from_registry(self):
        """Setup devices from the device registry configuration"""
        print("[Main] Setting up devices from registry...")
        print("=" * 60)

        device_count = 0
        failed_count = 0

        print(f"[Main] Processing {len(SIMULATOR_DEVICES)} configured devices...")

        for device_config in SIMULATOR_DEVICES:
            device_name = device_config["name"]
            sender_id = device_config["sender_id"]
            eep_type = device_config["eep_type"]
            interval = device_config["interval"]
            gateway_profile = device_config["gateway_profile"]

            # Store device info for reference
            sender_id_str = ':'.join(f'{b:02X}' for b in sender_id)
            self.device_registry[sender_id_str] = {
                'name': device_name,
                'eep_type': eep_type.value,
                'gateway_profile': gateway_profile,
                'interval': interval
            }

            success = self.simulator.add_device(
                name=device_name,
                sender_id=sender_id,
                eep_type=eep_type,
                base_telegram=None,
                interval=interval
            )

            if success:
                device_count += 1
                print(f"[Main] ✓ {device_name} ({gateway_profile}) -> ID: {sender_id.hex()}")
            else:
                failed_count += 1
                print(f"[Main] ✗ Failed to add {device_name}")

        print("=" * 60)
        print(f"[Main] Device Summary: {device_count} added successfully, {failed_count} failed")

        # Generate gateway configuration file
        if not Path(self.gateway_config_file).exists():
            print(f"[Main] Creating gateway configuration file: {self.gateway_config_file}")
            save_gateway_config(self.gateway_config_file)
        else:
            print(f"[Main] Gateway configuration exists: {self.gateway_config_file}")

        return device_count

    async def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""

        def signal_handler():
            print(f"\n[Main] Received interrupt signal, stopping simulation...")
            self.running = False

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    async def start(self):
        """Start the simulator"""
        try:
            await self.setup_signal_handlers()

            if not await self.simulator.start():
                print("[Main] Failed to start simulator")
                return False

            device_count = await self.setup_devices_from_registry()

            print(f"[Main] Simulation started with {device_count} devices")
            print(f"[Main] Gateway config file: {self.gateway_config_file}")
            print("[Main] Press Ctrl+C to stop the simulation")
            print("=" * 60)

            self.running = True
            return True

        except Exception as e:
            print(f"[Main] Error starting simulator: {e}")
            return False

    async def run(self):
        """Main simulation loop with device monitoring"""
        try:
            status_counter = 0
            stats_counter = 0

            while self.running:
                await asyncio.sleep(1)
                status_counter += 1
                stats_counter += 1

                if status_counter >= 30:
                    device_count = self.simulator.get_device_count()
                    ready_count = len(self.simulator.device_manager.get_ready_devices())
                    print(f"[Main] Status: {device_count} devices active, {ready_count} ready to transmit")
                    status_counter = 0

                if stats_counter >= 300:
                    await self.print_detailed_stats()
                    stats_counter = 0

        except asyncio.CancelledError:
            print(f"\n[Main] Main task cancelled.")
        except Exception as e:
            print(f"[Main] Error in main loop: {e}")
        finally:
            self.running = False
            await self.cleanup()

    async def print_detailed_stats(self):
        """Print detailed device statistics with registry information"""
        devices = self.simulator.list_devices()
        if not devices:
            return

        print(f"\n[Main] === Device Statistics ===")
        print(f"Total devices: {len(devices)}")

        # Group by EEP profile
        eep_groups = {}
        for device in devices:
            sender_id = device.get('sender_id', 'unknown')
            registry_info = self.device_registry.get(sender_id, {})
            gateway_profile = registry_info.get('gateway_profile', 'unknown')

            if gateway_profile not in eep_groups:
                eep_groups[gateway_profile] = []
            eep_groups[gateway_profile].append(device)

        print("EEP Profile distribution:")
        for eep_profile, device_list in sorted(eep_groups.items()):
            print(f"  {eep_profile}: {len(device_list)} devices")
            for device in device_list[:3]:  # Show first 3 devices
                name = device.get('name', 'Unknown')
                sender_id = device.get('sender_id', 'Unknown')
                print(f"    - {name} ({sender_id})")
            if len(device_list) > 3:
                print(f"    ... and {len(device_list) - 3} more")

        print("=" * 30)

    async def cleanup(self):
        """Cleanup resources"""
        print("[Main] Cleaning up and stopping simulator...")
        try:
            await self.simulator.stop()
        except Exception as e:
            print(f"[Main] Error during cleanup: {e}")

    def list_configured_devices(self):
        """List all configured devices with their EEP mappings"""
        print("\n📋 === Configured Devices ===")
        for device_config in SIMULATOR_DEVICES:
            name = device_config["name"]
            sender_id = device_config["sender_id"]
            eep_type = device_config["eep_type"]
            gateway_profile = device_config["gateway_profile"]
            interval = device_config["interval"]

            sender_id_str = ':'.join(f'{b:02X}' for b in sender_id)

            print(f"Device: {name}")
            print(f"  Sender ID: {sender_id_str}")
            print(f"  Simulator EEP: {eep_type.value}")
            print(f"  Gateway Profile: {gateway_profile}")
            print(f"  Interval: {interval}s")
            print()

    def verify_gateway_config(self):
        """Verify that gateway configuration matches simulator devices"""
        if not Path(self.gateway_config_file).exists():
            print(f"❌ Gateway config file not found: {self.gateway_config_file}")
            return False

        try:
            with open(self.gateway_config_file, 'r') as f:
                gateway_config = json.load(f)

            gateway_devices = gateway_config.get('devices', {})

            print(f"\n🔍 === Configuration Verification ===")
            print(f"Simulator devices: {len(SIMULATOR_DEVICES)}")
            print(f"Gateway devices: {len(gateway_devices)}")

            mismatches = []
            for device_config in SIMULATOR_DEVICES:
                sender_id_str = ':'.join(f'{b:02X}' for b in device_config["sender_id"])

                if sender_id_str not in gateway_devices:
                    mismatches.append(f"Missing in gateway: {device_config['name']} ({sender_id_str})")
                else:
                    gateway_device = gateway_devices[sender_id_str]
                    expected_profile = device_config["gateway_profile"]
                    actual_profile = gateway_device.get("eep_profile")

                    if expected_profile != actual_profile:
                        mismatches.append(
                            f"Profile mismatch for {device_config['name']}: "
                            f"expected {expected_profile}, got {actual_profile}"
                        )

            if mismatches:
                print("❌ Configuration mismatches found:")
                for mismatch in mismatches:
                    print(f"  - {mismatch}")
                return False
            else:
                print("✅ All devices match between simulator and gateway")
                return True

        except Exception as e:
            print(f"❌ Error verifying gateway config: {e}")
            return False


async def main():
    """Main entry point with enhanced device management"""
    import argparse

    parser = argparse.ArgumentParser(description='Enhanced EnOcean Simulator with Device Registry')
    parser.add_argument('--gateway-config', default='devices.json', help='Gateway device configuration file')
    parser.add_argument('--list-devices', action='store_true', help='List configured devices and exit')
    parser.add_argument('--verify-config', action='store_true', help='Verify gateway configuration and exit')
    parser.add_argument('--create-config', action='store_true', help='Create gateway configuration file and exit')

    args = parser.parse_args()

    simulator = EnOceanSimulator(gateway_config_file=args.gateway_config)

    # Handle list devices
    if args.list_devices:
        simulator.list_configured_devices()
        return

    # Handle verify config
    if args.verify_config:
        simulator.verify_gateway_config()
        return

    # Handle create config
    if args.create_config:
        save_gateway_config(args.gateway_config)
        return

    # Start the simulator
    if await simulator.start():
        await simulator.run()
    else:
        print("[Main] Failed to start simulator")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("EnOcean Simulator - Enhanced with Device Registry")
    print("=" * 60)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Main] Simulation stopped by user.")
    except Exception as e:
        print(f"[Main] Fatal error: {e}")
        sys.exit(1)