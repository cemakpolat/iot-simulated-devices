
from typing import Dict, Any, Optional, List
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceId:
    """Device identifier value object"""
    value: str

    def __post_init__(self):
        if not self.value or len(self.value.split(':')) != 4:
            raise ValueError(f"Invalid device ID format: {self.value}")


@dataclass(frozen=True)
class EEPProfile:
    """EEP profile value object"""
    value: str

    def __post_init__(self):
        if not self.value or '-' not in self.value:
            raise ValueError(f"Invalid EEP profile format: {self.value}")


@dataclass
class DeviceConfig:
    device_id: DeviceId
    name: str
    eep_profile: EEPProfile
    device_type: str = "unknown"
    location: str = ""
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    description: str = ""
    enabled: bool = True

    # Add these missing fields that device_manager expects
    capabilities: List[str] = None
    interval: int = 0

    # Activity tracking
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    packet_count: int = 0

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

    def update_activity(self, timestamp: float = None):
        """Update device activity"""
        if timestamp is None:
            timestamp = time.time()

        if self.first_seen is None:
            self.first_seen = timestamp

        self.last_seen = timestamp
        self.packet_count += 1


@dataclass
class EEPSuggestion:
    """EEP profile suggestion from discovery"""
    eep_profile: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    decoded_data: Dict[str, Any]
    data_quality: float  # How reasonable the decoded values are


@dataclass
class ProcessedPacket:
    """Result of packet processing"""
    device_id: DeviceId
    device_name: str
    eep_profile: EEPProfile
    timestamp: float
    decoded_data: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None


@dataclass
class UnknownDevice:
    """Unknown device pending discovery"""
    device_id: str
    first_seen: float
    last_seen: float
    packet_count: int
    sample_packets: List[bytes]
    rorg_types: List[int]
    eep_suggestions: List[EEPSuggestion]
    status: str = "pending"  # pending, analyzed, registered, ignored


from enum import Enum


class StorageStatus(Enum):
    """
    Enumeration for the lifecycle status of a device in storage,
    particularly for unknown devices.
    """
    PENDING = "pending"
    REGISTERED = "registered"
    IGNORED = "ignored"

