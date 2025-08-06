#!/usr/bin/env python3
"""
Device Manager - Production-ready device state management
Uses your rich device schema with external EEP profile validation
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from enocean_gateway.domain.models import DeviceConfig, DeviceId, EEPProfile
from enocean_gateway.storage.json_repository import JSONDeviceRepository

from enocean_gateway.utils import Logger


class DeviceManager:
    """
    Production device manager supporting your rich device schema
    - Now fully compatible with the SOLID repository pattern
    - Maintains all existing functionality while using the new storage layer
    """

    def __init__(self, storage_type: str = "json", devices_file: str = "devices.json", eep_loader=None):
        self.storage_type = storage_type
        self.eep_loader = eep_loader
        self.logger = Logger()
        self.repository = JSONDeviceRepository(devices_file, self.logger)
        self.lock = threading.Lock()

        print(f"✅ Device Manager initialized with {storage_type.upper()} storage")

    def register_device(self, device_id: str, name: str, eep_profile: str, **kwargs) -> bool:
        """
        Register device using your rich schema
        Validates EEP profile against external configuration
        """
        with self.lock:
            try:
                # Validate EEP profile if loader available
                if self.eep_loader and not self.eep_loader.validate_eep_profile(eep_profile):
                    print(f"❌ Invalid EEP profile: {eep_profile}")
                    return False

                # Get capabilities from EEP profile if available
                capabilities = kwargs.get("capabilities", [])
                if self.eep_loader and not capabilities:
                    profile_info = self.eep_loader.get_eep_profile(eep_profile)
                    if profile_info:
                        capabilities = profile_info.capabilities

                # Create device configuration
                device_config = DeviceConfig(
                    device_id=DeviceId(device_id),
                    name=name,
                    eep_profile=EEPProfile(eep_profile),
                    device_type=kwargs.get('device_type', 'unknown'),
                    location=kwargs.get('location', 'Unknown'),
                    manufacturer=kwargs.get('manufacturer', 'Unknown'),
                    model=kwargs.get('model', 'Unknown'),
                    description=kwargs.get('description', ''),
                    capabilities=capabilities,
                    interval=kwargs.get('interval', 0),
                    first_seen=kwargs.get('first_seen'),
                    last_seen=kwargs.get('last_seen'),
                    packet_count=kwargs.get('packet_count', 0),
                    enabled=kwargs.get('enabled', True)
                )

                # Save using repository
                success = self.repository.save_device(device_config)

                if success:
                    print(f"✅ Device registered: {name} ({device_id}) -> {eep_profile}")
                    if capabilities:
                        print(f"   📋 Capabilities: {', '.join(capabilities)}")
                return success

            except Exception as e:
                print(f"❌ Failed to register device {device_id}: {e}")
                return False

    def update_device_activity(self, device_id: str, timestamp: float = None) -> bool:
        """
        Update device activity with smart status calculation
        Uses interval for expected activity monitoring
        """
        with self.lock:
            try:
                device = self.repository.get_device(DeviceId(device_id))
                if not device:
                    return False

                current_time = timestamp or time.time()

                # Update activity
                if device.first_seen is None:
                    device.first_seen = current_time

                device.last_seen = current_time
                device.packet_count = getattr(device, 'packet_count', 0) + 1

                # Save updated device
                return self.repository.save_device(device)

            except Exception as e:
                print(f"❌ Failed to update activity for {device_id}: {e}")
                return False

    def _calculate_smart_status(self, device: DeviceConfig, current_time: float) -> str:
        """
        Smart status calculation using device interval and capabilities
        Now works with DeviceConfig objects
        """
        last_seen = device.last_seen
        interval = getattr(device, 'interval', 0)

        if not last_seen:
            return "inactive"

        time_since_last_seen = current_time - last_seen

        # For devices with expected intervals
        if interval > 0:
            # Active if seen within 2x expected interval
            if time_since_last_seen < (interval * 2):
                return "active"
            # Recently active if within 5x expected interval
            elif time_since_last_seen < (interval * 5):
                return "recently_active"
            else:
                return "inactive"

        # For event-driven devices (switches, contacts)
        else:
            # Active if seen within last 5 minutes
            if time_since_last_seen < 300:
                return "active"
            # Recently active if within last hour
            elif time_since_last_seen < 3600:
                return "recently_active"
            else:
                return "inactive"

    def get_device(self, device_id: str) -> Optional[Dict]:
        """Get specific device with current status as dict"""
        with self.lock:
            try:
                device = self.repository.get_device(DeviceId(device_id))
                if not device:
                    return None

                # Convert to dict and add current status
                device_dict = self._device_config_to_dict(device)
                device_dict["status"] = self._calculate_smart_status(device, time.time())
                return device_dict

            except Exception as e:
                print(f"❌ Failed to get device {device_id}: {e}")
                return None

    def _device_config_to_dict(self, device: DeviceConfig) -> Dict:
        """Convert DeviceConfig to dict format expected by API"""
        return {
            "device_id": device.device_id.value,
            "name": device.name,
            "eep_profile": device.eep_profile.value,
            "device_type": device.device_type,
            "location": device.location,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "description": device.description,
            "capabilities": getattr(device, 'capabilities', []),
            "interval": getattr(device, 'interval', 0),
            "last_seen": device.last_seen,
            "first_seen": device.first_seen,
            "packet_count": getattr(device, 'packet_count', 0),
            "enabled": device.enabled,
            "registered_at": getattr(device, 'registered_at', None)
        }

    def list_devices(self) -> List[Dict]:
        """List all devices with current status"""

        devices = []
        current_time = time.time()

        for device_config in self.repository.list_devices():
            # Convert to dict and add status
            device_dict = self._device_config_to_dict(device_config)
            device_dict["status"] = self._calculate_smart_status(device_config, current_time)
            devices.append(device_dict)

        return devices

    def remove_device(self, device_id: str) -> bool:
        """Remove a device"""
        with self.lock:
            try:
                return self.repository.remove_device(DeviceId(device_id))
            except Exception as e:
                print(f"❌ Failed to remove device {device_id}: {e}")
                return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics using your rich schema"""
        with self.lock:
            devices = self.list_devices()
            current_time = time.time()

            stats = {
                "total_devices": len(devices),
                "active_devices": len([d for d in devices if d.get("status") == "active"]),
                "recently_active_devices": len([d for d in devices if d.get("status") == "recently_active"]),
                "inactive_devices": len([d for d in devices if d.get("status") == "inactive"]),
                "total_packets": sum(d.get("packet_count", 0) for d in devices),

                # Your schema analytics
                "device_types": {},
                "eep_profiles": {},
                "locations": {},
                "capabilities": {},
                "manufacturers": {}
            }

            # Enhanced analytics using your rich data
            for device in devices:
                # Device types
                device_type = device.get("device_type", "unknown")
                stats["device_types"][device_type] = stats["device_types"].get(device_type, 0) + 1

                # EEP profiles
                eep_profile = device.get("eep_profile", "unknown")
                stats["eep_profiles"][eep_profile] = stats["eep_profiles"].get(eep_profile, 0) + 1

                # Locations
                location = device.get("location", "Unknown")
                stats["locations"][location] = stats["locations"].get(location, 0) + 1

                # Capabilities
                for capability in device.get("capabilities", []):
                    stats["capabilities"][capability] = stats["capabilities"].get(capability, 0) + 1

                # Manufacturers
                manufacturer = device.get("manufacturer", "Unknown")
                stats["manufacturers"][manufacturer] = stats["manufacturers"].get(manufacturer, 0) + 1

            return stats

    def get_devices_by_capability(self, capability: str) -> List[Dict]:
        """Get devices that have a specific capability"""
        devices = self.list_devices()
        return [
            device for device in devices
            if capability in device.get("capabilities", [])
        ]

    def get_devices_by_location(self, location: str) -> List[Dict]:
        """Get devices at a specific location"""
        devices = self.list_devices()
        return [
            device for device in devices
            if device.get("location") == location
        ]

    def get_overdue_devices(self) -> List[Dict]:
        """Get devices that are overdue based on their expected interval"""
        devices = self.list_devices()
        current_time = time.time()
        overdue = []

        for device in devices:
            interval = device.get("interval", 0)
            last_seen = device.get("last_seen")

            if interval > 0 and last_seen:
                time_since_last_seen = current_time - last_seen
                if time_since_last_seen > (interval * 3):  # 3x expected interval
                    device["overdue_by"] = time_since_last_seen - interval
                    overdue.append(device)

        return overdue

    def device_exists(self, device_id: str) -> bool:
        """Check if device exists"""
        with self.lock:
            try:
                device = self.repository.get_device(DeviceId(device_id))
                return device is not None
            except Exception:
                return False

    def get_registered_device_ids(self) -> set:
        """Get set of all registered device IDs for sync operations"""
        with self.lock:
            devices = self.repository.list_devices()
            return {d.device_id.value for d in devices}

    def validate_device_schema(self, device_data: Dict) -> List[str]:
        """Validate device data against your schema"""
        errors = []

        required_fields = ["name", "eep_profile", "device_type"]
        for field in required_fields:
            if field not in device_data:
                errors.append(f"Missing required field: {field}")

        # Validate EEP profile
        if self.eep_loader and "eep_profile" in device_data:
            if not self.eep_loader.validate_eep_profile(device_data["eep_profile"]):
                errors.append(f"Invalid EEP profile: {device_data['eep_profile']}")

        # Validate capabilities format
        if "capabilities" in device_data:
            if not isinstance(device_data["capabilities"], list):
                errors.append("Capabilities must be a list")

        # Validate interval
        if "interval" in device_data:
            try:
                interval = int(device_data["interval"])
                if interval < 0:
                    errors.append("Interval must be non-negative")
            except (ValueError, TypeError):
                errors.append("Interval must be a number")

        return errors

