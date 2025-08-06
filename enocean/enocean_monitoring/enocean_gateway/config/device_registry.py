# src/config/device_registry.py
"""
Device Registry Manager for EnOcean Gateway
Maps sender_id to EEP profiles and device information
"""

import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from ..utils.logger import Logger


TEACH_IN_TO_EEP_MAP = {
    # Teach-in signature -> (Real EEP, Device Info Dictionary)
    "D2_EMSIA_MULTI_SENSOR": ("D2-14-40", {
        "name": "STM 550 Multi-Sensor",
        "device_type": "multi_sensor",
        "manufacturer": "Emsia",
        "model": "DS Easyfit STM 550",
        "description": "Multi-sensor for temperature, humidity, contact, and acceleration.",
        "capabilities": ["temperature", "humidity", "contact", "acceleration"]
    }),
    # You can add other known devices here. For example, a standard rocker switch:
    "F6-XX-XX": ("F6-02-01", {
        "name": "Rocker Switch",
        "device_type": "rocker_switch",
        "manufacturer": "EnOcean",
        "model": "PTM 21x Series",
        "description": "2-button rocker switch.",
        "capabilities": ["switch"]
    }),
    # Example for a standard contact sensor (window/door)
    "D5-00-01": ("D5-00-01", {
        "name": "Contact Sensor",
        "device_type": "contact_sensor",
        "manufacturer": "EnOcean",
        "model": "STM 33x",
        "description": "Magnetic contact sensor for doors or windows.",
        "capabilities": ["contact"]
    })
}


class DeviceInfo:
    """Represents a single device configuration"""

    def __init__(self, sender_id: str, config: Dict[str, Any]):
        self.sender_id = sender_id
        self.name = config.get('name', f'Device_{sender_id}')
        self.eep_profile = config.get('eep_profile')
        self.device_type = config.get('device_type', 'unknown')
        self.location = config.get('location', 'Unknown')
        self.manufacturer = config.get('manufacturer', 'Unknown')
        self.model = config.get('model', 'Unknown')
        self.description = config.get('description', '')
        self.capabilities = config.get('capabilities', [])
        self.interval = config.get('interval', 0)
        self.last_seen = config.get('last_seen')
        self.status = config.get('status', 'unknown')
        self.packet_count = 0
        self.first_seen = None

    def update_activity(self, timestamp: float = None):
        """Update device activity timestamp"""
        if timestamp is None:
            timestamp = time.time()

        if self.first_seen is None:
            self.first_seen = timestamp

        self.last_seen = timestamp
        self.packet_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'sender_id': self.sender_id,
            'name': self.name,
            'eep_profile': self.eep_profile,
            'device_type': self.device_type,
            'location': self.location,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'description': self.description,
            'capabilities': self.capabilities,
            'interval': self.interval,
            'last_seen': self.last_seen,
            'status': self.status,
            'packet_count': self.packet_count,
            'first_seen': self.first_seen
        }


class DeviceRegistry:
    """Manages device configuration and EEP profile mapping"""

    def __init__(self, config_file: str = "devices.json", logger: Logger = None):
        self.config_file = Path(config_file)
        self.logger = logger
        self.devices: Dict[str, DeviceInfo] = {}
        self.locations: Dict[str, Dict[str, Any]] = {}
        self.eep_profiles: Dict[str, Dict[str, Any]] = {}
        self.config_modified = False

        self.load_configuration()

    def load_configuration(self) -> bool:
        """Load device configuration from JSON file"""
        try:
            if not self.config_file.exists():
                if self.logger:
                    self.logger.warning(f"Device config file not found: {self.config_file}")
                self._create_default_config()
                return False

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            # Load devices
            devices_config = config.get('devices', {})
            for sender_id, device_config in devices_config.items():
                self.devices[sender_id] = DeviceInfo(sender_id, device_config)

            # Load locations and EEP profiles
            self.locations = config.get('locations', {})
            self.eep_profiles = config.get('eep_profiles', {})

            if self.logger:
                self.logger.success(f"Loaded {len(self.devices)} devices from {self.config_file}")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load device config: {e}")
            return False

    def save_configuration(self) -> bool:
        """Save current configuration to JSON file"""
        try:
            config = {
                'version': '1.0',
                'devices': {
                    sender_id: {
                        'name': device.name,
                        'eep_profile': device.eep_profile,
                        'device_type': device.device_type,
                        'location': device.location,
                        'manufacturer': device.manufacturer,
                        'model': device.model,
                        'description': device.description,
                        'capabilities': device.capabilities,
                        'interval': device.interval,
                        'last_seen': device.last_seen,
                        'status': device.status
                    }
                    for sender_id, device in self.devices.items()
                },
                'locations': self.locations,
                'eep_profiles': self.eep_profiles
            }

            # Create backup
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.bak')
                self.config_file.rename(backup_file)

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            self.config_modified = False

            if self.logger:
                self.logger.info(f"Device configuration saved to {self.config_file}")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save device config: {e}")
            return False

    def get_device(self, sender_id: str) -> Optional[DeviceInfo]:
        """Get device information by sender_id"""
        return self.devices.get(sender_id)

    def get_eep_profile(self, sender_id: str) -> Optional[str]:
        """Get EEP profile for a device"""
        device = self.devices.get(sender_id)
        return device.eep_profile if device else None

    def register_device(self, sender_id: str, eep_profile: str, **kwargs) -> DeviceInfo:
        """Register a new device or update existing one"""
        if sender_id in self.devices:
            device = self.devices[sender_id]
            # Update existing device
            if eep_profile and device.eep_profile != eep_profile:
                device.eep_profile = eep_profile
                self.config_modified = True
        else:
            # Create new device
            device_config = {
                'eep_profile': eep_profile,
                'name': kwargs.get('name', f'Device_{sender_id}'),
                'device_type': kwargs.get('device_type', 'unknown'),
                'location': kwargs.get('location', 'Unknown'),
                'manufacturer': kwargs.get('manufacturer', 'Unknown'),
                'model': kwargs.get('model', 'Unknown'),
                'description': kwargs.get('description', ''),
                'capabilities': kwargs.get('capabilities', []),
                'interval': kwargs.get('interval', 0),
                'status': 'discovered'
            }
            device = DeviceInfo(sender_id, device_config)
            self.devices[sender_id] = device
            self.config_modified = True

            if self.logger:
                self.logger.info(f"Registered new device: {sender_id} -> {eep_profile}")

        return device

    def update_device_activity(self, sender_id: str, timestamp: float = None):
        """Update device activity"""
        device = self.devices.get(sender_id)
        print("sender_id")
        if device:
            device.update_activity(timestamp)
            # Mark as active if it was discovered
            if device.status == 'discovered':
                device.status = 'active'
                print(f"{device.status}")
                self.config_modified = True

    def remove_device(self, sender_id: str) -> bool:
        """Remove a device from registry"""
        if sender_id in self.devices:
            del self.devices[sender_id]
            self.config_modified = True
            if self.logger:
                self.logger.info(f"Removed device: {sender_id}")
            return True
        return False

    def get_all_devices(self) -> Dict[str, DeviceInfo]:
        """Get all registered devices"""
        return self.devices.copy()

    def get_devices_by_location(self, location: str) -> List[DeviceInfo]:
        """Get devices by location"""
        return [device for device in self.devices.values() if device.location == location]

    def get_devices_by_type(self, device_type: str) -> List[DeviceInfo]:
        """Get devices by type"""
        return [device for device in self.devices.values() if device.device_type == device_type]

    def get_devices_by_eep(self, eep_profile: str) -> List[DeviceInfo]:
        """Get devices by EEP profile"""
        return [device for device in self.devices.values() if device.eep_profile == eep_profile]

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_devices = len(self.devices)
        active_devices = sum(1 for d in self.devices.values() if d.status == 'active')
        device_types = {}
        eep_profiles = {}
        locations = {}

        for device in self.devices.values():
            device_types[device.device_type] = device_types.get(device.device_type, 0) + 1
            if device.eep_profile:
                eep_profiles[device.eep_profile] = eep_profiles.get(device.eep_profile, 0) + 1
            locations[device.location] = locations.get(device.location, 0) + 1

        return {
            'total_devices': total_devices,
            'active_devices': active_devices,
            'discovered_devices': sum(1 for d in self.devices.values() if d.status == 'discovered'),
            'inactive_devices': sum(1 for d in self.devices.values() if d.status == 'inactive'),
            'device_types': device_types,
            'eep_profiles': eep_profiles,
            'locations': locations,
            'total_packets': sum(d.packet_count for d in self.devices.values())
        }

    def validate_device_config(self, sender_id: str) -> List[str]:
        """Validate device configuration and return list of issues"""
        issues = []
        device = self.devices.get(sender_id)

        if not device:
            issues.append(f"Device {sender_id} not found")
            return issues
        if not device.eep_profile:
            issues.append("Missing EEP profile")
        elif device.eep_profile not in self.eep_profiles:
            issues.append(f"Unknown EEP profile: {device.eep_profile}")
        if not device.name or device.name.startswith('Device_'):
            issues.append("Device needs a proper name")
        if device.location == 'Unknown':
            issues.append("Device location not set")
        return issues

    def auto_save_if_modified(self):
        """Auto-save configuration if it has been modified"""
        if self.config_modified:
            self.save_configuration()

    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            'version': '1.0',
            'devices': {},
            'locations': {'Unknown': {'building': 'Main', 'floor': 1, 'zone': 'general'}},
            'eep_profiles': {
                'A5-04-01': {'description': 'Temperature and humidity sensor',
                             'capabilities': ['temperature', 'humidity']},
                'F6-02-01': {'description': 'Rocker switch', 'capabilities': ['switch']},
                'D5-00-01': {'description': 'Contact sensor', 'capabilities': ['contact']},
                'D2-14-40': {'description': 'EMSIA Multi-Sensor',
                             'capabilities': ['temperature', 'humidity', 'contact', 'acceleration']}
            }
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            if self.logger:
                self.logger.info(f"Created default device config: {self.config_file}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create default config: {e}")


class DeviceDiscovery:
    """Handles automatic device discovery and registration"""

    def __init__(self, registry: DeviceRegistry, logger: Logger = None):
        self.registry = registry
        self.logger = logger
        self.discovery_mode = True  # Enable discovery by default
        self.discovered_devices = set()

    def enable_discovery(self):
        """Enable device discovery mode"""
        self.discovery_mode = True
        if self.logger:
            self.logger.info("Device discovery mode enabled")

    def disable_discovery(self):
        """Disable device discovery mode"""
        self.discovery_mode = False
        if self.logger:
            self.logger.info("Device discovery mode disabled")

    def handle_unknown_device(self, sender_id: str, rorg: int, data: bytes) -> Optional[str]:
        """
        Handles a packet from an unknown device by identifying its teach-in telegram.
        If the teach-in is recognized, it registers the device with its proper operational EEP.
        """
        if not self.discovery_mode:
            return None

        # Generate a "signature" from the teach-in packet to identify the device type.
        teach_in_signature = self._guess_teach_in_signature(rorg, data)

        if not teach_in_signature:
            # This is a data packet from an unknown device, or an unrecognized teach-in. Ignore it.
            return None

        # Log the discovery attempt
        if self.logger:
            self.logger.info(f"Received teach-in from unknown device {sender_id} with signature: {teach_in_signature}")

        # Check if we know what to do with this teach-in signature
        if teach_in_signature in TEACH_IN_TO_EEP_MAP:
            operational_eep, device_info = TEACH_IN_TO_EEP_MAP[teach_in_signature]

            # Register the device using its REAL operational profile and metadata
            self.registry.register_device(
                sender_id=sender_id,
                eep_profile=operational_eep,
                **device_info
            )

            # Add to a temporary set to avoid re-registering from duplicate teach-in packets
            self.discovered_devices.add(sender_id)

            if self.logger:
                self.logger.success(
                    f"Successfully registered device {sender_id} ({device_info.get('model')}) with EEP {operational_eep}")

            # Return the operational EEP so the packet decoder can process this first packet
            return operational_eep
        else:
            if self.logger:
                self.logger.warning(f"Unrecognized teach-in signature '{teach_in_signature}' from {sender_id}. "
                                    f"Device not registered. Consider adding it to TEACH_IN_TO_EEP_MAP.")
            return None

    def _guess_teach_in_signature(self, rorg: int, data: bytes) -> Optional[str]:
        """
        Creates a unique signature from a telegram to identify the device type during teach-in.
        Assumes `data` is the raw payload received from the radio (including RORG byte).
        """
        # The 'data' payload starts with the RORG byte.
        # rorg_from_data = data[0]

        if rorg == 0xD2:  # VLD - Used by your Emsia sensor
            # The unique signature for this device is in the 2nd and 3rd bytes of the packet.
            if len(data) >= 3:
                return f"D2-{data[1]:02X}-{data[2]:02X}"  # This will produce "D2-A6-DE"

        elif rorg == 0xF6:  # RPS - Rocker Switches
            # Most rocker switch teach-ins are generic.
            return "F6-XX-XX"

        elif rorg == 0xD5:  # 1BS - Contact Sensors
            # Simple 1BS devices often teach-in by just sending their data packet.
            return "D5-00-01"

        elif rorg == 0xA5:  # 4BS - More complex sensors
            # The standard way to identify a 4BS teach-in is by checking a specific bit.
            # T21 (Teach-in bit) is bit 3 of DB0 (last byte). Teach-in is active when this bit is 0.
            if len(data) > 0 and (data[-1] & 0x08) == 0:
                # A standard UTE teach-in telegram. We can build a signature from it.
                # The EEP is usually in DB3, DB2, DB1 (if they exist)
                if len(data) >= 4:
                    # Example signature: A5-04-01 (from DB3, DB2, DB1)
                    return f"A5-{data[-4]:02X}-{data[-3]:02X}-{data[-2]:02X}"

        # If no teach-in pattern is matched, return None
        return None
