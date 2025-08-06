"""
Unified EnOcean System - Clean integration of all components
Merges your existing domain logic with SOLID architecture and discovery
"""

from abc import ABC, abstractmethod
from ..domain.models import *


class DeviceRepository(ABC):
    """Abstract repository for device storage"""

    @abstractmethod
    def get_device(self, device_id: DeviceId) -> Optional[DeviceConfig]:
        pass

    @abstractmethod
    def save_device(self, device: DeviceConfig) -> bool:
        pass

    @abstractmethod
    def remove_device(self, device_id: DeviceId) -> bool:
        pass

    @abstractmethod
    def list_devices(self) -> List[DeviceConfig]:
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        pass
