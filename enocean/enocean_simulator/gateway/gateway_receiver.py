# File: gateway/gateway_receiver.py - ENHANCED VERSION with File Logging
import asyncio
import serial
import time
import os
import json
import csv
from datetime import datetime
from typing import Optional
from protocol.decoder import EEPDecoder
from protocol.esp3 import ESP3Protocol
from gateway.device_manager import DeviceManager


class GatewayReceiver:
    """Enhanced receiver that processes telegrams and logs everything to files"""

    def __init__(self, device_manager: DeviceManager, port='/dev/ttys007', log_dir='logs'):
        self.device_manager = device_manager
        self.port: Optional[str] = None
        self.running = False
        self.receiver_task: Optional[asyncio.Task] = None
        self.buffer = bytearray()

        # Logging setup
        self.log_dir = log_dir
        self.setup_logging()

        # Statistics
        self.stats = {
            'total_telegrams': 0,
            'successful_telegrams': 0,
            'failed_telegrams': 0,
            'unknown_devices': 0,
            'checksum_failures': 0,
            'devices_seen': set(),
            'start_time': None
        }

    def setup_logging(self):
        """Setup logging directories and files"""
        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

        # Generate timestamp for this session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Setup file paths
        self.raw_log_file = os.path.join(self.log_dir, f"raw_telegrams_{timestamp}.log")
        self.decoded_log_file = os.path.join(self.log_dir, f"decoded_data_{timestamp}.log")
        self.csv_log_file = os.path.join(self.log_dir, f"device_data_{timestamp}.csv")
        self.stats_file = os.path.join(self.log_dir, f"session_stats_{timestamp}.json")
        self.error_log_file = os.path.join(self.log_dir, f"errors_{timestamp}.log")

        # Initialize CSV file with headers
        self.init_csv_log()

        print(f"[GatewayReceiver] Logging to directory: {self.log_dir}")
        print(f"[GatewayReceiver] Raw telegrams: {self.raw_log_file}")
        print(f"[GatewayReceiver] Decoded data: {self.decoded_log_file}")
        print(f"[GatewayReceiver] CSV data: {self.csv_log_file}")

    def init_csv_log(self):
        """Initialize CSV log file with headers"""
        try:
            with open(self.csv_log_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'Timestamp', 'Device_Name', 'Device_ID', 'EEP_Type',
                    'Raw_Telegram', 'Payload', 'Decoded_Data', 'Status'
                ])
        except Exception as e:
            print(f"[GatewayReceiver] Error initializing CSV log: {e}")

    def log_raw_telegram(self, telegram: bytes, status: str = "SUCCESS"):
        """Log raw telegram data"""
        try:
            timestamp = datetime.now().isoformat()
            with open(self.raw_log_file, 'a') as f:
                f.write(f"{timestamp} | {status} | {telegram.hex()} | Length: {len(telegram)}\n")
        except Exception as e:
            print(f"[GatewayReceiver] Error logging raw telegram: {e}")

    def log_decoded_data(self, device_name: str, device_id: str, eep_type: str, decoded_data: dict):
        """Log decoded device data"""
        try:
            timestamp = datetime.now().isoformat()
            with open(self.decoded_log_file, 'a') as f:
                f.write(f"{timestamp} | {device_name} ({device_id}) | {eep_type} | {json.dumps(decoded_data)}\n")
        except Exception as e:
            print(f"[GatewayReceiver] Error logging decoded data: {e}")

    def log_csv_data(self, device_name: str, device_id: str, eep_type: str,
                     raw_telegram: str, payload: str, decoded_data: dict, status: str):
        """Log data to CSV file for easy analysis"""
        try:
            timestamp = datetime.now().isoformat()
            with open(self.csv_log_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    timestamp, device_name, device_id, eep_type,
                    raw_telegram, payload, json.dumps(decoded_data), status
                ])
        except Exception as e:
            print(f"[GatewayReceiver] Error logging CSV data: {e}")

    def log_error(self, error_type: str, error_msg: str, telegram_hex: str = ""):
        """Log errors to separate error file"""
        try:
            timestamp = datetime.now().isoformat()
            with open(self.error_log_file, 'a') as f:
                f.write(f"{timestamp} | {error_type} | {error_msg} | {telegram_hex}\n")
        except Exception as e:
            print(f"[GatewayReceiver] Error logging error: {e}")

    def save_statistics(self):
        """Save session statistics to JSON file"""
        try:
            self.stats['devices_seen'] = list(self.stats['devices_seen'])  # Convert set to list for JSON
            self.stats['end_time'] = datetime.now().isoformat()
            if self.stats['start_time']:
                start = datetime.fromisoformat(self.stats['start_time'])
                end = datetime.fromisoformat(self.stats['end_time'])
                self.stats['session_duration_seconds'] = (end - start).total_seconds()

            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"[GatewayReceiver] Error saving statistics: {e}")

    async def start(self, port: str):
        """Start the gateway receiver"""
        self.port = port
        self.running = True
        self.stats['start_time'] = datetime.now().isoformat()

        # Start the receiver task
        self.receiver_task = asyncio.create_task(self._receiver_loop())

        print(f"[GatewayReceiver] Started on {port}")

    async def stop(self):
        """Stop the gateway receiver"""
        self.running = False

        if self.receiver_task and not self.receiver_task.done():
            self.receiver_task.cancel()
            try:
                await self.receiver_task
            except asyncio.CancelledError:
                pass

        # Save final statistics
        self.save_statistics()
        self.print_session_summary()
        print("[GatewayReceiver] Stopped")

    def print_session_summary(self):
        """Print session summary"""
        print(f"\n[GatewayReceiver] === SESSION SUMMARY ===")
        print(f"Total telegrams processed: {self.stats['total_telegrams']}")
        print(f"Successful: {self.stats['successful_telegrams']}")
        print(f"Failed: {self.stats['failed_telegrams']}")
        print(f"Unknown devices: {self.stats['unknown_devices']}")
        print(f"Checksum failures: {self.stats['checksum_failures']}")
        print(f"Unique devices seen: {len(self.stats['devices_seen'])}")
        print(f"Log files saved in: {self.log_dir}")
        print("=" * 40)

    async def _receiver_loop(self):
        """Main receiver loop with enhanced logging"""
        try:
            with serial.Serial(self.port, 57600, timeout=0.1) as ser:
                print(f"[GatewayReceiver] Receiver loop started")

                while self.running:
                    try:
                        if ser.in_waiting > 0:
                            # Read new data and add to buffer
                            new_data = ser.read(ser.in_waiting)
                            if new_data:
                                self.buffer.extend(new_data)
                                # Process all complete telegrams in buffer
                                await self._process_buffer()

                        # Small delay to prevent excessive CPU usage
                        await asyncio.sleep(0.01)

                        # Print stats every 100 telegrams
                        if self.stats['total_telegrams'] % 100 == 0 and self.stats['total_telegrams'] > 0:
                            self.print_periodic_stats()

                    except Exception as e:
                        error_msg = f"Error reading from serial: {e}"
                        print(f"[GatewayReceiver] {error_msg}")
                        self.log_error("SERIAL_READ", error_msg)
                        await asyncio.sleep(1)

        except Exception as e:
            error_msg = f"Failed to open serial port: {e}"
            print(f"[GatewayReceiver] {error_msg}")
            self.log_error("SERIAL_OPEN", error_msg)

    def print_periodic_stats(self):
        """Print periodic statistics"""
        success_rate = (self.stats['successful_telegrams'] / self.stats['total_telegrams']) * 100
        print(f"[GatewayReceiver] Stats: {self.stats['total_telegrams']} total, "
              f"{self.stats['successful_telegrams']} success ({success_rate:.1f}%), "
              f"{len(self.stats['devices_seen'])} devices")

    async def _process_buffer(self):
        """Process all complete telegrams in the buffer"""
        while len(self.buffer) > 0:
            # Look for ESP3 sync byte (0x55)
            sync_pos = self.buffer.find(0x55)

            if sync_pos == -1:
                # No sync byte found, clear buffer
                if len(self.buffer) > 0:
                    self.log_error("SYNC_NOT_FOUND", f"No sync byte in buffer", self.buffer.hex())
                self.buffer.clear()
                return

            # Remove any data before sync byte
            if sync_pos > 0:
                discarded = self.buffer[:sync_pos]
                self.log_error("DATA_DISCARDED", f"Discarded {len(discarded)} bytes before sync", discarded.hex())
                self.buffer = self.buffer[sync_pos:]

            # Check if we have enough data for header (6 bytes)
            if len(self.buffer) < 6:
                return  # Wait for more data

            # Extract header information
            data_length = (self.buffer[1] << 8) | self.buffer[2]
            optional_length = self.buffer[3]
            packet_type = self.buffer[4]

            # Calculate total telegram length
            total_length = 6 + data_length + optional_length + 1  # +1 for checksum

            # Validate telegram length
            if total_length > 1000:  # Sanity check
                self.log_error("INVALID_LENGTH", f"Telegram too long: {total_length} bytes", self.buffer[:20].hex())
                self.buffer = self.buffer[1:]  # Skip one byte and try again
                continue

            # Check if we have the complete telegram
            if len(self.buffer) < total_length:
                return  # Wait for more data

            # Extract the complete telegram
            telegram = bytes(self.buffer[:total_length])

            # Remove processed telegram from buffer
            self.buffer = self.buffer[total_length:]

            # Process this telegram
            await self._process_single_telegram(telegram)

    async def _process_single_telegram(self, telegram: bytes):
        """Process a single complete telegram with comprehensive logging"""
        self.stats['total_telegrams'] += 1

        try:
            # Log raw telegram
            self.log_raw_telegram(telegram, "RECEIVED")

            # Verify checksum
            if not self._verify_checksum(telegram):
                self.stats['checksum_failures'] += 1
                self.stats['failed_telegrams'] += 1
                error_msg = f"Checksum verification failed"
                print(f"[GatewayReceiver] {error_msg}: {telegram.hex()}")
                self.log_error("CHECKSUM_FAIL", error_msg, telegram.hex())
                self.log_csv_data("UNKNOWN", "UNKNOWN", "UNKNOWN", telegram.hex(), "", {}, "CHECKSUM_FAIL")
                return

            # Extract payload (data portion)
            data_length = (telegram[1] << 8) | telegram[2]
            optional_length = telegram[3]
            payload_start = 6
            payload_end = 6 + data_length + optional_length
            payload = telegram[payload_start:payload_end]

            # Extract sender ID and find corresponding device
            sender_id = ESP3Protocol.extract_sender_id(telegram)
            device = self.device_manager.get_device_by_sender_id(sender_id)

            if device:
                # Device found - decode and log
                self.stats['successful_telegrams'] += 1
                self.stats['devices_seen'].add(device.name)

                try:
                    # Decode using device's EEP type
                    decoded = EEPDecoder.decode(device.eep_type, payload)

                    # Log successful decoding
                    print(f"[GatewayReceiver] {device.name} ({device.eep_type.value}): {decoded}")
                    self.log_decoded_data(device.name, sender_id.hex(), device.eep_type.value, decoded)
                    self.log_csv_data(device.name, sender_id.hex(), device.eep_type.value,
                                      telegram.hex(), payload.hex(), decoded, "SUCCESS")

                except Exception as decode_error:
                    # Decoding failed but device is known
                    self.stats['failed_telegrams'] += 1
                    error_msg = f"Decoding failed for {device.name}: {decode_error}"
                    print(f"[GatewayReceiver] {error_msg}")
                    self.log_error("DECODE_FAIL", error_msg, telegram.hex())
                    self.log_csv_data(device.name, sender_id.hex(), device.eep_type.value,
                                      telegram.hex(), payload.hex(), {"error": str(decode_error)}, "DECODE_FAIL")
            else:
                # Unknown device
                self.stats['unknown_devices'] += 1
                self.stats['failed_telegrams'] += 1
                error_msg = f"Unknown device with ID {sender_id.hex()}"
                print(f"[GatewayReceiver] {error_msg}: {payload.hex()}")
                self.log_error("UNKNOWN_DEVICE", error_msg, telegram.hex())
                self.log_csv_data("UNKNOWN", sender_id.hex(), "UNKNOWN",
                                  telegram.hex(), payload.hex(), {"raw_payload": payload.hex()}, "UNKNOWN_DEVICE")

        except Exception as e:
            self.stats['failed_telegrams'] += 1
            error_msg = f"Error processing telegram: {e}"
            print(f"[GatewayReceiver] {error_msg}")
            self.log_error("PROCESS_ERROR", error_msg, telegram.hex())

    def _verify_checksum(self, telegram: bytes) -> bool:
        """Verify ESP3 telegram checksums with detailed logging"""
        try:
            if len(telegram) < 7:
                self.log_error("CHECKSUM_ERROR", f"Telegram too short for checksum: {len(telegram)} bytes",
                               telegram.hex())
                return False

            # Header checksum verification using CRC8
            header_checksum_calculated = ESP3Protocol.crc8(telegram[1:5])
            header_checksum_received = telegram[5]

            if header_checksum_calculated != header_checksum_received:
                error_msg = f"Header checksum mismatch: calculated={header_checksum_calculated:02X}, received={header_checksum_received:02X}"
                self.log_error("HEADER_CHECKSUM", error_msg, telegram.hex())
                return False

            # Data checksum verification using CRC8
            data_length = (telegram[1] << 8) | telegram[2]
            optional_length = telegram[3]
            data_start = 6
            data_end = 6 + data_length + optional_length

            if data_end >= len(telegram):
                error_msg = f"Invalid telegram length for data checksum: data_end={data_end}, telegram_len={len(telegram)}"
                self.log_error("LENGTH_ERROR", error_msg, telegram.hex())
                return False

            data_checksum_calculated = ESP3Protocol.crc8(telegram[data_start:data_end])
            data_checksum_received = telegram[-1]

            if data_checksum_calculated != data_checksum_received:
                error_msg = f"Data checksum mismatch: calculated={data_checksum_calculated:02X}, received={data_checksum_received:02X}"
                self.log_error("DATA_CHECKSUM", error_msg, telegram.hex())
                return False

            return True

        except Exception as e:
            error_msg = f"Error verifying checksum: {e}"
            self.log_error("CHECKSUM_EXCEPTION", error_msg, telegram.hex())
            return False