# File: protocol/esp3.py - CORRECTED VERSION
class ESP3Protocol:
    """ESP3 protocol utilities for EnOcean telegrams - FIXED"""

    SYNC_BYTE = 0x55
    PACKET_TYPE_RADIO = 0x01

    @staticmethod
    def crc8(data: bytes, polynomial: int = 0x07) -> int:
        """Calculate CRC8 checksum using specified polynomial"""
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc

    @staticmethod
    def create_telegram(rorg: int, data: bytes, sender_id: bytes, status: int = 0x00) -> bytes:
        """Create a complete ESP3 telegram - CORRECTED"""

        # Data portion = RORG + data + sender_id + status
        # This creates the actual radio telegram data
        payload = bytes([rorg]) + data + sender_id + bytes([status])

        # Header: data_length(2) + optional_length(1) + packet_type(1)
        data_length = len(payload)
        optional_length = 0  # No optional data
        header = data_length.to_bytes(2, 'big') + bytes([optional_length, ESP3Protocol.PACKET_TYPE_RADIO])

        # Calculate header checksum using CRC8
        header_checksum = ESP3Protocol.crc8(header)

        # Calculate data checksum using CRC8 (only over the payload)
        data_checksum = ESP3Protocol.crc8(payload)

        # Complete telegram: sync + header + header_checksum + payload + data_checksum
        telegram = (bytes([ESP3Protocol.SYNC_BYTE]) +
                    header +
                    bytes([header_checksum]) +
                    payload +
                    bytes([data_checksum]))

        return telegram

    @staticmethod
    def update_telegram_checksums(telegram: bytearray) -> bytearray:
        """Update both checksums in ESP3 telegram - CORRECTED"""
        if len(telegram) < 7:
            return telegram

        # Header checksum (CRC8H): covers bytes 1-4 (data_length + optional_length + packet_type)
        header_checksum = ESP3Protocol.crc8(telegram[1:5])
        telegram[5] = header_checksum

        # Data checksum (CRC8D): covers the payload only
        data_length = (telegram[1] << 8) | telegram[2]
        optional_length = telegram[3]

        # Payload starts at byte 6, length = data_length + optional_length
        payload_start = 6
        payload_end = 6 + data_length + optional_length

        if payload_end <= len(telegram) - 1:  # Ensure we don't include the checksum byte
            data_checksum = ESP3Protocol.crc8(telegram[payload_start:payload_end])
            telegram[payload_end] = data_checksum  # Place checksum at the end

        return telegram

    @staticmethod
    def verify_checksums(telegram: bytes) -> bool:
        """Verify both checksums in ESP3 telegram"""
        if len(telegram) < 7:
            return False

        # Verify header checksum
        header_crc = ESP3Protocol.crc8(telegram[1:5])
        if header_crc != telegram[5]:
            return False

        # Verify data checksum
        data_length = (telegram[1] << 8) | telegram[2]
        optional_length = telegram[3]
        payload_start = 6
        payload_end = 6 + data_length + optional_length

        if payload_end >= len(telegram):
            return False

        data_crc = ESP3Protocol.crc8(telegram[payload_start:payload_end])
        return data_crc == telegram[-1]

    @staticmethod
    def extract_sender_id(telegram: bytes) -> bytes:
        """Extract sender ID from ESP3 telegram """
        if len(telegram) < 11:  # Minimum for A5 telegram
            return b'\x00\x00\x00\x00'

        data_length = (telegram[1] << 8) | telegram[2]

        # For radio telegrams, sender ID is always the last 4 bytes of data before status
        # Structure: RORG(1) + DATA(n) + SENDER_ID(4) + STATUS(1)
        if data_length >= 6:  # Minimum: RORG + SENDER_ID + STATUS
            # Sender ID starts at: 6 (start of payload) + data_length - 5 (last 5 bytes are sender_id + status)
            sender_id_start = 6 + data_length - 5
            return telegram[sender_id_start:sender_id_start + 4]

        return b'\x00\x00\x00\x00'

    @staticmethod
    def extract_payload(telegram: bytes) -> bytes:
        """Extract the complete payload (RORG + DATA + SENDER_ID + STATUS)"""
        if len(telegram) < 7:
            return b''

        data_length = (telegram[1] << 8) | telegram[2]
        optional_length = telegram[3]

        payload_start = 6
        payload_end = 6 + data_length + optional_length

        if payload_end <= len(telegram) - 1:  # Exclude the data checksum
            return telegram[payload_start:payload_end]

        return b''

    @staticmethod
    def debug_telegram(telegram: bytes) -> dict:
        """Debug telegram structure - useful for troubleshooting"""
        if len(telegram) < 6:
            return {"error": "Telegram too short"}

        info = {
            "sync": f"0x{telegram[0]:02X}",
            "data_length": (telegram[1] << 8) | telegram[2],
            "optional_length": telegram[3],
            "packet_type": f"0x{telegram[4]:02X}",
            "header_crc": f"0x{telegram[5]:02X}",
            "total_length": len(telegram)
        }

        payload = ESP3Protocol.extract_payload(telegram)
        if payload:
            info["payload"] = payload.hex()
            info["payload_length"] = len(payload)

            if len(payload) >= 1:
                info["rorg"] = f"0x{payload[0]:02X}"

            if len(payload) >= 6:  # A5 telegram minimum
                info["sender_id"] = payload[-5:-1].hex()
                info["status"] = f"0x{payload[-1]:02X}"

        if len(telegram) >= 7:
            info["data_crc"] = f"0x{telegram[-1]:02X}"

        return info