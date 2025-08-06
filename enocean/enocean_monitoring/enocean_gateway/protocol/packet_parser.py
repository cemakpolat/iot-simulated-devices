# src/protocol/packet_parser.py
"""
EnOcean packet parsing functionality
"""

import time
from typing import List, Dict, Any, Optional
from ..utils.logger import Logger


class EnOceanPacket:
    """Represents a successfully parsed EnOcean packet with all fields separated."""

    def __init__(self, raw_packet: bytes, rorg: int, data: bytes, sender_id: str, status: int,
                 timestamp: Optional[float] = None):
        self.raw_packet = raw_packet
        self.rorg = rorg
        self.data = data  # This is now JUST RORG + Sensor Data
        self.sender_id = sender_id
        self.status = status
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary for logging or other uses."""
        return {
            'raw_packet': self.raw_packet.hex().upper(),
            'rorg': self.rorg,
            'data': self.data.hex().upper(),
            'sender_id': self.sender_id,
            'status': self.status,
            'timestamp': self.timestamp,
        }


class PacketParser:
    """Parses raw serial data into EnOcean packets (Corrected for ESP3 Type 1)."""

    def __init__(self, logger):
        self.logger = logger
        self.buffer = bytearray()
        self.sync_byte = 0x55

    def parse_buffer(self, raw_data: bytearray) -> List[EnOceanPacket]:
        """Parse raw data buffer and extract valid ESP3 packets."""
        packets = []
        self.buffer.extend(raw_data)

        while True:
            packet = self._extract_one_packet()
            if packet:
                packets.append(packet)
            else:
                break  # No more complete packets in buffer
        return packets

    def _extract_one_packet(self) -> Optional[EnOceanPacket]:
        """Finds and parses one complete and valid ESP3 packet from the buffer."""
        # This state machine will robustly find a valid packet.
        while len(self.buffer) >= 7:  # Minimum possible packet length
            sync_pos = self.buffer.find(self.sync_byte)
            if sync_pos == -1:
                self.buffer.clear()
                return None

            if sync_pos > 0:
                self.buffer = self.buffer[sync_pos:]

            if len(self.buffer) < 6: return None  # Not enough for a header

            # --- Header Parsing and Validation ---
            header_bytes = self.buffer[1:5]
            crc8h = self.buffer[5]
            if self._calculate_crc8(header_bytes) != crc8h:
                self.logger.warning(
                    f"Invalid ESP3 Header CRC. Discarding sync byte and retrying. Buffer: {self.buffer.hex()}")
                self.buffer = self.buffer[1:]
                continue

            # Header is valid, extract lengths
            data_length = (self.buffer[1] << 8) | self.buffer[2]
            optional_length = self.buffer[3]
            packet_type = self.buffer[4]

            total_packet_len = 6 + data_length + optional_length + 1  # Header + Data + Optional + CRC8D

            if len(self.buffer) < total_packet_len:
                return None  # Not enough data yet, wait for more

            # --- Full Packet Extraction & Validation ---
            full_packet_bytes = self.buffer[:total_packet_len]
            data_and_optional = full_packet_bytes[6:-1]
            crc8d = full_packet_bytes[-1]

            if self._calculate_crc8(data_and_optional) != crc8d:
                self.logger.warning("Invalid ESP3 Data CRC. Discarding packet.")
                self.buffer = self.buffer[1:]
                continue

            # --- Packet is VALID, now parse its contents ---
            # Consume the valid packet from the buffer FIRST
            self.buffer = self.buffer[total_packet_len:]

            if packet_type == 0x01:  # Radio Packet
                return self._parse_radio_packet(full_packet_bytes)
            else:
                self.logger.info(f"Skipping non-radio packet of type {packet_type}")
                # We consumed it, so we don't return it, just loop for the next one

        return None  # No full packet found or processed in this pass

    def _parse_radio_packet(self, packet_bytes: bytes) -> Optional[EnOceanPacket]:
        """Correctly separates the fields of a valid ESP3 Type 1 Radio Packet."""
        try:
            data_length = (packet_bytes[1] << 8) | packet_bytes[2]
            # The full data payload as defined by ESP3
            full_data_payload = packet_bytes[6: 6 + data_length]

            # The structure of the data payload is fixed for radio packets
            if len(full_data_payload) < 6:  # RORG(1) + DATA(at least 0) + SENDER(4) + STATUS(1)
                self.logger.warning(f"Radio packet data payload is too short: {len(full_data_payload)}")
                return None

            # --- THE CRITICAL FIX IS HERE ---
            rorg = full_data_payload[0]
            status = full_data_payload[-1]
            sender_id_bytes = full_data_payload[-5:-1]
            sender_id_str = ':'.join(f'{b:02X}' for b in sender_id_bytes)

            # The data for EEP decoders is the payload MINUS the sender and status.
            eep_data = full_data_payload[:-5]

            return EnOceanPacket(
                raw_packet=packet_bytes,
                rorg=rorg,
                data=eep_data,
                sender_id=sender_id_str,
                status=status
            )
        except IndexError:
            self.logger.error("Error parsing radio packet fields due to unexpected length.")
            return None

    def _calculate_crc8(self, data: bytes) -> int:
        """Standard CRC-8-ATM H.222 calculation for EnOcean."""
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x07
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc


class PacketStatistics:
    """Track packet parsing statistics"""

    def __init__(self):
        self.total_packets = 0
        self.valid_packets = 0
        self.invalid_packets = 0
        self.crc_errors = 0
        self.unknown_packets = 0
        self.packets_by_type = {}
        self.packets_by_device = {}

    def record_packet(self, packet: Optional[EnOceanPacket], valid: bool = True):
        """Record packet statistics"""
        self.total_packets += 1

        if packet and valid:
            self.valid_packets += 1

            # Track by RORG type
            rorg = f"0x{packet.rorg:02X}"
            self.packets_by_type[rorg] = self.packets_by_type.get(rorg, 0) + 1

            # Track by device
            device_id = packet.sender_id
            self.packets_by_device[device_id] = self.packets_by_device.get(device_id, 0) + 1
        else:
            self.invalid_packets += 1

    def record_crc_error(self):
        """Record CRC error"""
        self.crc_errors += 1

    def record_unknown_packet(self):
        """Record unknown packet type"""
        self.unknown_packets += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics summary"""
        return {
            'total_packets': self.total_packets,
            'valid_packets': self.valid_packets,
            'invalid_packets': self.invalid_packets,
            'crc_errors': self.crc_errors,
            'unknown_packets': self.unknown_packets,
            'success_rate': (self.valid_packets / self.total_packets * 100) if self.total_packets > 0 else 0,
            'packets_by_type': self.packets_by_type,
            'packets_by_device': self.packets_by_device,
            'unique_devices': len(self.packets_by_device)
        }

    def reset(self):
        """Reset all statistics"""
        self.total_packets = 0
        self.valid_packets = 0
        self.invalid_packets = 0
        self.crc_errors = 0
        self.unknown_packets = 0
        self.packets_by_type.clear()
        self.packets_by_device.clear()