#!/usr/bin/env python3
"""
Main Entry Point for the EnOcean Gateway
Initializes and runs all gateway components, including the web server,
device manager, and state synchronizer.
"""

import sys
import time
import argparse
import traceback
from pathlib import Path
from threading import Thread
from typing import Optional, Any

# Add project root to Python path for clean imports
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from enocean_gateway.device_manager import DeviceManager
    from enocean_gateway.config.eep_profile_loader import EEPProfileLoader
    from enocean_gateway.core.synchronizer import StateSynchronizer
    from enocean_gateway.core.gateway import create_system_from_config, UnifiedEnOceanSystem
    from enocean_gateway.web.server import create_web_app
except ImportError as e:
    print(f"❌ Critical Import Error: {e}")
    print("💡 Please ensure all required modules (device_manager, web_server, etc.) are present in the "
          "'enocean_gateway' directory.")
    sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments for the gateway."""
    parser = argparse.ArgumentParser(
        description='EnOcean Gateway - A modular and robust management system.',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python main.py                     # Start with web interface on default port
  python main.py --port 8080         # Use a custom port for the web server
  python main.py --no-web            # Run in command-line only mode
  python main.py --interactive       # Run with an interactive command prompt
"""
    )
    parser.add_argument('--config', default='.env', help='Path to the environment configuration file (default: .env)')
    parser.add_argument('--config-dir', default='enocean_gateway/config', help='Directory for EEP profiles (default: config)')
    parser.add_argument('--storage', choices=['json', 'sqlite'], default='json',
                        help='Storage type for device data (default: json)')
    parser.add_argument('--devices-file', default='devices.json',
                        help='Filename for JSON device storage (default: devices.json)')
    parser.add_argument('--port', type=int, default=5001, help='Port for the web server (default: 5001)')
    parser.add_argument('--no-web', action='store_true', help='Disable the web interface and run in headless mode')
    parser.add_argument('--interactive', action='store_true', help='Enable an interactive command-line interface')
    return parser.parse_args()


def initialize_components(args: argparse.Namespace) -> dict[str, Any]:
    """Initializes all gateway components based on arguments."""
    print("🚀 Initializing EnOcean Gateway components...")
    print("=" * 60)

    components = {
        "eep_loader": None,
        "device_manager": None,
        "enocean_system": None,
        "synchronizer": None,
    }

    # Step 1: Initialize EEP Profile Loader
    if Path(args.config_dir).exists():
        components["eep_loader"] = EEPProfileLoader(config_dir=args.config_dir)
        print(f"✅ EEP Loader: {len(components['eep_loader'].get_all_eep_profiles())} profiles loaded.")
    else:
        print("⚠️ EEP Profile Loader: Config directory not found, continuing without.")

    # Step 2: Initialize Device Manager
    components["device_manager"] = DeviceManager(
        storage_type=args.storage,
        devices_file=args.devices_file,
        eep_loader=components["eep_loader"]
    )
    print("✅ Device Manager: Initialized successfully.")

    # Step 3: Initialize EnOcean System
    try:
        system = create_system_from_config(
            args.config,
            args.storage,
            components["eep_loader"]  # Pass the loader here
        )
        if system.start():
            components["enocean_system"] = system
            print("✅ EnOcean System: Connection established.")
        else:
            print("⚠️ EnOcean System: Failed to start. Running in device management-only mode.")
    except Exception as e:
        print(f"⚠️ EnOcean System: Error during initialization ({e}). Running in device management-only mode.")

    # Step 4: Initialize State Synchronizer
    components["synchronizer"] = StateSynchronizer(components["device_manager"], components["enocean_system"])
    components["synchronizer"].start()
    print("✅ State Synchronizer: Started and running.")

    return components


def start_web_server(args: argparse.Namespace, components: dict[str, Any]):
    """Starts the Flask web server in a separate thread if enabled."""
    if args.no_web:
        print("ℹ️ Web server is disabled by --no-web flag.")
        return

    web_app = create_web_app(
        components["device_manager"],
        components["enocean_system"],
        components["synchronizer"],
        components["eep_loader"]
    )

    def run_web():
        try:
            # Use werkzeug's run_simple for better production-like behavior than app.run
            from werkzeug.serving import run_simple
            run_simple(hostname='0.0.0.0', port=args.port, application=web_app, threaded=True)
        except Exception as e:
            print(f"❌ Web server crashed: {e}")

    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()
    time.sleep(1)  # Give the server a moment to start
    print(f"✅ Web Server: Running on http://localhost:{args.port}")


def print_startup_info(args: argparse.Namespace, components: dict[str, Any]):
    """Prints a summary of the gateway's status after initialization."""
    dm = components.get("device_manager")
    sync = components.get("synchronizer")

    print("\n✅ EnOcean Gateway Startup Complete!")
    print("=" * 60)

    if dm:
        stats = dm.get_statistics()
        print(f"📱 Device Manager: {stats.get('total_devices', 0)} devices loaded from {args.storage.upper()} storage.")
    if sync:
        sync_stats = sync.get_sync_statistics()
        last_sync_time = sync_stats.get('last_sync_time')
        last_sync_str = time.ctime(last_sync_time) if last_sync_time else 'Never'
        print(f"🔄 State Synchronizer: Running. Last sync at {last_sync_str}.")
    if components.get("enocean_system"):
        print("📡 EnOcean System: Connected and processing packets.")
    else:
        print("📡 EnOcean System: Not connected. Operating in management-only mode.")
    if not args.no_web:
        print(f"🌐 Web Interface: Access at http://localhost:{args.port}/")

    print("=" * 60)


def run_interactive_mode(components: dict[str, Any]):
    """Runs the gateway with an interactive command-line prompt."""
    print("\n📋 Interactive mode. Type 'help' for commands or Ctrl+C to exit.")
    dm = components.get("device_manager")
    system = components.get("enocean_system")
    sync = components.get("synchronizer")

    while True:
        try:
            cmd = input("\ngateway> ").strip().lower()
            if cmd in ["quit", "exit", "q"]:
                break
            elif not cmd:
                continue

            if cmd == "help":
                print(
                    "\nAvailable commands:\n  stats    - Show system statistics\n  devices  - List registered devices\n  unknown  - List unknown devices\n  sync     - Force state synchronization\n  quit     - Exit")
            elif cmd == "stats" and dm:
                print(f"📊 Device Stats: {dm.get_statistics()}")
            elif cmd == "devices" and dm:
                devices = dm.list_devices()
                print(f"📱 Registered Devices ({len(devices)}):")
                for dev in devices[:10]:
                    status_icon = {"active": "🟢", "recently_active": "🟡", "inactive": "🔴"}.get(dev.get("status"), "⚪")
                    print(f"  {status_icon} {dev.get('name')} ({dev.get('device_id')})")
            elif cmd == "unknown" and system:
                unknown = system.get_unknown_devices()
                print(f"🔍 Unknown Devices ({len(unknown)}):")
                for dev in unknown[:5]:
                    print(f"  🟡 {dev.device_id}")
            elif cmd == "sync" and sync:
                sync.force_sync()
                print("✅ Sync completed.")
            else:
                print(f"❓ Unknown command or component not available: {cmd}")
        except (EOFError, KeyboardInterrupt):
            break


def run_normal_mode(enocean_system: Optional[UnifiedEnOceanSystem]):
    """Runs the gateway in a non-interactive, monitoring mode."""
    print("📋 Gateway running in normal mode. Press Ctrl+C to exit.")
    if not enocean_system:
        print("ℹ️ No active EnOcean system. Gateway is idle.")
        # We can just sleep indefinitely if there's nothing to do
        while True: time.sleep(3600)

    while True:
        try:
            enocean_system.process_packets_from_serial()
            time.sleep(0.01)  # Prevent busy-waiting
        except Exception as e:
            print(f"❌ Unhandled error in main loop: {e}")
            time.sleep(5)  # Wait before retrying


def main():
    """Main execution function."""
    args = parse_arguments()
    components = {}

    try:
        components = initialize_components(args)
        start_web_server(args, components)
        print_startup_info(args, components)

        if args.interactive:
            run_interactive_mode(components)
        else:
            run_normal_mode(components.get("enocean_system"))

    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ A critical error occurred: {e}")
        traceback.print_exc()
        return 1
    finally:
        if components.get("synchronizer"):
            components["synchronizer"].stop()
        if components.get("enocean_system"):
            components["enocean_system"].stop()
        print("✅ Gateway stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
