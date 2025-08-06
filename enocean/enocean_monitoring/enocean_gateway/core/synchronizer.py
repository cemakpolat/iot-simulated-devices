#!/usr/bin/env python3
"""
State Synchronizer - A clean and robust module for ensuring data consistency
between the Device Manager and the EnOcean System.
"""

import time
import threading
import traceback
from typing import Dict, Any, Optional

# Assuming these are the base classes or type hints
from ..device_manager import DeviceManager
from ..core.gateway import UnifiedEnOceanSystem


class StateSynchronizer:
    """
    Synchronizes state between the device manager and the EnOcean system.

    Responsibilities:
    - Periodically removes registered devices from the discovery/unknown list.
    - Triggers immediate sync actions on events like device registration.
    """

    def __init__(
            self,
            device_manager: DeviceManager,
            enocean_system: Optional[UnifiedEnOceanSystem],
            sync_interval: int = 60  # Syncing every 5s is very frequent; 60s is more reasonable.
    ):
        """
        Initializes the StateSynchronizer.

        Args:
            device_manager: The manager for registered device configurations.
            enocean_system: The core system handling real-time packet processing.
            sync_interval: The interval in seconds for the periodic background sync.
        """
        self.device_manager = device_manager
        self.enocean_system = enocean_system
        self.sync_interval = sync_interval

        self.lock = threading.Lock()
        self._running = False
        self._sync_thread = None
        self.last_sync_time: Optional[float] = None

        print("✅ State Synchronizer initialized.")

    def start(self):
        """Starts the background synchronization thread."""
        if self._running:
            return
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        print(f"🔄 State synchronizer started (syncing every {self.sync_interval}s).")

    def stop(self):
        """Stops the synchronization thread gracefully."""
        self._running = False
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=3)
        print("🛑 State synchronizer stopped.")

    def is_running(self) -> bool:
        """Checks if the synchronizer is running."""
        return self._running

    def force_sync(self):
        """Forces an immediate, one-time synchronization."""
        print("⏳ Performing manual synchronization...")
        if self._perform_sync():
            print("✅ Manual sync completed successfully.")
        else:
            print("❌ Manual sync failed.")

    def _sync_loop(self):
        """The main background loop for periodic synchronization."""
        while self._running:
            try:
                self._perform_sync()
            except Exception as e:
                print(f"❌ Unhandled error in sync loop: {e}")
                traceback.print_exc()

            # Wait for the next interval, even if the sync fails
            time.sleep(self.sync_interval)

    def _perform_sync(self) -> bool:
        """
        Performs the core synchronization logic.
        This is the single source of truth for synchronization.
        """
        # Do not sync if the EnOcean system is not available.
        if not self.enocean_system:
            return True  # Nothing to do, so it's a "success"

        with self.lock:
            try:
                # 1. Get all registered device IDs from the source of truth (DeviceManager).
                registered_ids = self.device_manager.get_registered_device_ids()

                # 2. Tell the EnOcean system to clean itself up using this list.
                #    The synchronizer doesn't need to know *how* it's done.
                cleaned_count = self.enocean_system.clean_unknown_devices(registered_ids)

                if cleaned_count > 0:
                    print(f"🔄 Sync: Cleaned {cleaned_count} newly registered device(s) from the unknown list.")

                self.last_sync_time = time.time()
                return True
            except Exception as e:
                print(f"❌ Synchronization failed: {e}")
                traceback.print_exc()
                return False

    def on_device_registered(self, device_id: str):
        """
        Callback for when a device is registered. Triggers an immediate sync.

        This simplifies logic by just calling the main sync routine, which is robust
        and handles all necessary cleanup.
        """
        print(f"⚡ Device '{device_id}' registered. Triggering immediate state sync.")
        # Running the full sync is simple, robust, and avoids duplicate logic.
        # It's fast enough that running it on-demand is fine.
        self.force_sync()

    def on_device_ignored(self, device_id: str):
        """Callback for when an unknown device is marked as ignored."""
        if self.enocean_system and hasattr(self.enocean_system, 'ignore_unknown_device'):
            try:
                self.enocean_system.ignore_unknown_device(device_id)
                print(f"🚫 Device '{device_id}' marked as ignored in the EnOcean system.")
            except Exception as e:
                print(f"❌ Failed to mark device '{device_id}' as ignored: {e}")

    def get_sync_statistics(self) -> Dict[str, Any]:
        """Gathers and returns key statistics about the synchronization state."""
        with self.lock:
            stats = {
                "sync_running": self.is_running(),
                "last_sync_time": self.last_sync_time,
                "sync_interval": self.sync_interval,
                "real_system_connected": self.enocean_system is not None,
            }
            # The device manager and enocean system are now the sources of truth for their own stats.
            # This method can be expanded to fetch stats from them if needed,
            # but it should not calculate them itself.
            return stats