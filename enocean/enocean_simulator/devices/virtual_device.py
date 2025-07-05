# File: devices/virtual_device.py
import asyncio
import time
from typing import Optional
from protocol.enums import EEPType


class VirtualDevice:
    """Lightweight virtual EnOcean device for gateway simulation"""

    def __init__(self, name: str, sender_id: bytes, eep_type: EEPType,
                 base_telegram: bytes, interval: float = 5.0):
        self.name = name
        self.sender_id = sender_id
        self.eep_type = eep_type
        self.base_telegram = base_telegram
        self.interval = interval
        self.last_transmission = 0
        self.task: Optional[asyncio.Task] = None
        self.running = False

    def should_transmit(self) -> bool:
        """Check if device should transmit based on interval"""
        current_time = time.time()
        return (current_time - self.last_transmission) >= self.interval

    def mark_transmitted(self):
        """Mark that device has transmitted"""
        self.last_transmission = time.time()

    def get_sender_id_hex(self) -> str:
        """Get sender ID as hex string"""
        return self.sender_id.hex().upper()

    def __str__(self):
        return f"VirtualDevice(name='{self.name}', eep='{self.eep_type.value}', id={self.get_sender_id_hex()})"


