# src/connections/serial_connection.py
"""
Serial connection handler for EnOcean devices
"""

import serial
import time
from typing import Optional, List
from ..utils.logger import Logger


class SerialConnection:
    """Handles serial communication with EnOcean devices"""

    def __init__(self, port: str, baud_rate: int, logger: Logger, timeout: float = 1.0):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.logger = logger
        self.connection: Optional[serial.Serial] = None

    def connect(self) -> bool:
        """Establish serial connection"""
        try:
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout
            )
            self.logger.success(f"Serial connected: {self.port}@{self.baud_rate}")
            return True
        except Exception as e:
            self.logger.failure(f"Serial connection failed: {e}")
            return False

    def disconnect(self):
        """Close serial connection"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            self.logger.info("Serial connection closed")

    def is_connected(self) -> bool:
        """Check if serial connection is active"""
        return self.connection is not None and self.connection.is_open

    def read_available(self) -> Optional[bytearray]:
        """Read available data from serial port"""
        if not self.is_connected():
            return None

        try:
            if self.connection.in_waiting > 0:
                data = self.connection.read(self.connection.in_waiting)
                return bytearray(data)
        except Exception as e:
            self.logger.debug(f"Serial read error: {e}")

        return None

    def write(self, data: bytes) -> bool:
        """Write data to serial port"""
        if not self.is_connected():
            return False

        try:
            self.connection.write(data)
            return True
        except Exception as e:
            self.logger.error(f"Serial write error: {e}")
            return False

    def flush(self):
        """Flush serial buffers"""
        if self.is_connected():
            try:
                self.connection.flushInput()
                self.connection.flushOutput()
            except Exception as e:
                self.logger.debug(f"Serial flush error: {e}")


class SerialManager:
    """Manages multiple serial connections if needed"""

    def __init__(self, logger: Logger):
        self.logger = logger
        self.connections: dict = {}

    def add_connection(self, name: str, port: str, baud_rate: int) -> bool:
        """Add a new serial connection"""
        connection = SerialConnection(port, baud_rate, self.logger)
        if connection.connect():
            self.connections[name] = connection
            return True
        return False

    def remove_connection(self, name: str):
        """Remove a serial connection"""
        if name in self.connections:
            self.connections[name].disconnect()
            del self.connections[name]

    def get_connection(self, name: str) -> Optional[SerialConnection]:
        """Get a serial connection by name"""
        return self.connections.get(name)

    def disconnect_all(self):
        """Disconnect all serial connections"""
        for connection in self.connections.values():
            connection.disconnect()
        self.connections.clear()