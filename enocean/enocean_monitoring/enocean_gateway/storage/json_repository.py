import json
from pathlib import Path
from .repositories import DeviceRepository
from ..utils.logger import Logger
from ..domain.models import *


class JSONDeviceRepository(DeviceRepository):
    """JSON-based device storage - integrates with your existing format"""

    def __init__(self, file_path: str = "devices.json", logger: Logger = None):
        self.file_path = Path(file_path)
        self.logger = logger
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.file_path.exists():
            self._save_data({
                "version": "1.0",
                "devices": {},
                "locations": {
                    "Unknown": {"building": "Main", "floor": 1, "zone": "general"}
                },
                "eep_profiles": {
                    "A5-04-01": {"description": "Temperature and humidity sensor",
                                 "capabilities": ["temperature", "humidity"]},
                    "F6-02-01": {"description": "Rocker switch", "capabilities": ["switch"]},
                    "D5-00-01": {"description": "Contact sensor", "capabilities": ["contact"]},
                    "D2-14-40": {"description": "Multi-sensor",
                                 "capabilities": ["temperature", "humidity", "contact", "acceleration"]}
                }
            })

    def _load_data(self) -> Dict:
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load devices: {e}")
            return {"version": "1.0", "devices": {}}

    def _save_data(self, data: Dict):
        # Create backup
        if self.file_path.exists():
            backup_file = self.file_path.with_suffix('.bak')
            if backup_file.exists():
                backup_file.unlink()  # Remove old backup
            self.file_path.rename(backup_file)

        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def save_device(self, device: DeviceConfig) -> bool:
        try:
            data = self._load_data()
            data["devices"][device.device_id.value] = {
                "name": device.name,
                "eep_profile": device.eep_profile.value,
                "device_type": device.device_type,
                "location": device.location,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "description": device.description,
                "enabled": device.enabled,
                "capabilities": device.capabilities,  # Add this
                "interval": device.interval,  # Add this
                "first_seen": device.first_seen,
                "last_seen": device.last_seen,
                "packet_count": device.packet_count
            }
            self._save_data(data)
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save device: {e}")
            return False

    def get_device(self, device_id: DeviceId) -> Optional[DeviceConfig]:
        data = self._load_data()
        device_data = data.get("devices", {}).get(device_id.value)
        if not device_data:
            return None

        return DeviceConfig(
            device_id=device_id,
            name=device_data["name"],
            eep_profile=EEPProfile(device_data["eep_profile"]),
            device_type=device_data.get("device_type", "unknown"),
            location=device_data.get("location", ""),
            manufacturer=device_data.get("manufacturer", "Unknown"),
            model=device_data.get("model", "Unknown"),
            description=device_data.get("description", ""),
            enabled=device_data.get("enabled", True),
            capabilities=device_data.get("capabilities", []),  # Add this
            interval=device_data.get("interval", 0),  # Add this
            first_seen=device_data.get("first_seen"),
            last_seen=device_data.get("last_seen"),
            packet_count=device_data.get("packet_count", 0)
        )

    def remove_device(self, device_id: DeviceId) -> bool:
        try:
            data = self._load_data()

            if device_id.value in data.get("devices", {}):
                del data["devices"][device_id.value]
                self._save_data(data)

                if self.logger:
                    self.logger.info(f"Removed device: {device_id.value}")

                return True
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to remove device: {e}")
            return False

    def list_devices(self) -> List[DeviceConfig]:
        data = self._load_data()
        devices = []

        for device_id_str, device_data in data.get("devices", {}).items():
            try:
                device = DeviceConfig(
                    device_id=DeviceId(device_id_str),
                    name=device_data["name"],
                    eep_profile=EEPProfile(device_data["eep_profile"]),
                    device_type=device_data.get("device_type", "unknown"),
                    location=device_data.get("location", ""),
                    manufacturer=device_data.get("manufacturer", "Unknown"),
                    model=device_data.get("model", "Unknown"),
                    description=device_data.get("description", ""),
                    enabled=device_data.get("enabled", True),
                    first_seen=device_data.get("first_seen"),
                    last_seen=device_data.get("last_seen"),
                    packet_count=device_data.get("packet_count", 0)
                )
                devices.append(device)
            except ValueError as e:
                if self.logger:
                    self.logger.warning(f"Invalid device data for {device_id_str}: {e}")

        return devices
    
    def get_all_devices(self) -> List[DeviceConfig]:
        return self.list_devices()

    def get_statistics(self) -> Dict[str, Any]:
        devices = self.list_devices()

        stats = {
            "total_devices": len(devices),
            "active_devices": sum(1 for d in devices if d.enabled and d.last_seen),
            "device_types": {},
            "eep_profiles": {},
            "locations": {},
            "total_packets": sum(d.packet_count for d in devices)
        }

        for device in devices:
            # Count by type
            stats["device_types"][device.device_type] = \
                stats["device_types"].get(device.device_type, 0) + 1

            # Count by EEP
            stats["eep_profiles"][device.eep_profile.value] = \
                stats["eep_profiles"].get(device.eep_profile.value, 0) + 1

            # Count by location
            location = device.location or "Unknown"
            stats["locations"][location] = \
                stats["locations"].get(location, 0) + 1

        return stats
