#!/usr/bin/env python3
import os
import serial
import time
import threading
from queue import Queue
import json
import warnings
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv('.env')

warnings.filterwarnings("ignore")

# --- Environment variables with defaults ---
# PORT = os.getenv('ENOCEAN_DEVICE', '/dev/tty.usbserial-FT6U7YM1')
PORT = os.getenv('ENOCEAN_DEVICE', '/dev/ttys007')

BAUD_RATE = int(os.getenv('ENOCEAN_BAUD', '57600'))
MQTT_BROKER = os.getenv('MQTT_BROKER', 'broker.emqx.io')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'enocean/sensors')
MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'enocean_gateway')
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'


class EnOceanGateway:
    def __init__(self):
        self.serial_conn = None
        self.mqtt_client = None
        self.running = False
        self.packet_queue = Queue()
        self.devices = {}

    def connect_serial(self):
        try:
            self.serial_conn = serial.Serial(PORT, BAUD_RATE, timeout=1)
            print(f"✅ Serial connected: {PORT}@{BAUD_RATE}")
            return True
        except Exception as e:
            print(f"❌ Serial error: {e}")
            return False

    def connect_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID,
                                           callback_api_version=CallbackAPIVersion.VERSION2)
            self.mqtt_client.on_connect = lambda c, u, f, r, p=None: print(f"✅ MQTT connected: {r}")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"❌ MQTT error: {e}")
            return False

    def read_packets(self):
        buffer = bytearray()
        while self.running:
            try:
                if self.serial_conn.in_waiting:
                    buffer.extend(self.serial_conn.read(self.serial_conn.in_waiting))
                    while len(buffer) >= 6:
                        sync_pos = buffer.find(0x55)
                        if sync_pos == -1:
                            buffer.clear()
                            break
                        if sync_pos > 0:
                            buffer = buffer[sync_pos:]

                        if len(buffer) < 6:
                            break

                        data_len = (buffer[1] << 8) | buffer[2]
                        opt_len = buffer[3]
                        total_len = 6 + data_len + opt_len + 1

                        if len(buffer) < total_len:
                            break

                        packet_data = buffer[:total_len]
                        buffer = buffer[total_len:]

                        # Extract sender ID
                        sender_id = "unknown"
                        if data_len >= 5:
                            payload = packet_data[6:6 + data_len]
                            if len(payload) >= 5:
                                sender_bytes = payload[-5:-1]
                                sender_id = ':'.join(f"{b:02X}" for b in sender_bytes)

                        packet = {
                            'data': packet_data[6:6 + data_len],
                            'sender_id': sender_id,
                            'timestamp': time.time(),
                            'status': packet_data[6 + data_len + opt_len - 1] if opt_len > 0 else 0
                        }

                        self.packet_queue.put(packet)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if DEBUG:
                    print(f"Read error: {e}")
                time.sleep(0.1)

    def decode_packet(self, packet):
        if not packet.get('data') or len(packet['data']) == 0:
            return None

        data = packet['data']
        rorg = data[0]
        sender_id = packet['sender_id']
        timestamp = packet['timestamp']

        result = {
            'device_id': sender_id,
            'timestamp': timestamp,
            'rorg': f"0x{rorg:02X}",
            'signal_quality': self._get_signal_quality(packet.get('status', 0))
        }

        # Add enhanced RORG handling
        if rorg == 0xD2:  # Variable Length Data (VLD)
            result.update(self._decode_d2(data[1:-5] if len(data) > 5 else data[1:]))
        elif rorg == 0xA5:  # 4-Byte Sensor (4BS)
            result.update(self._decode_a5(data[1:5] if len(data) > 4 else data[1:]))
        elif rorg == 0xF6:  # Rocker Switch (RPS)
            result.update(self._decode_f6(data[1:2] if len(data) > 1 else []))
        elif rorg == 0xD4:  # Universal Teach-In
            result.update(self._decode_d4(data[1:]))
        elif rorg == 0xD5:  # Contact sensors
            result.update(self._decode_d5(data[1:2] if len(data) > 1 else []))
        elif rorg == 0xA7:  # Smart Ack
            result.update({'type': 'smart_ack', 'command': data[1] if len(data) > 1 else 0})
        elif rorg == 0x30:  # Secure devices
            result.update({'type': 'secure', 'security_level': data[1] if len(data) > 1 else 0})
        else:
            result['type'] = 'unknown'
            result['raw_data'] = data.hex().upper()
            # Add detailed analysis for debugging
            result['analysis'] = self._analyze_unknown_packet(data)

        return result

    def _decode_d5(self, payload):
        """Decode D5 packets (contact sensors)"""
        if not payload:
            return {'type': 'contact', 'state': 'unknown'}

        state = payload[0]
        return {
            'type': 'contact',
            'state': 'open' if state == 0x00 else 'closed',
            'raw': f"0x{state:02X}"
        }
    def _analyze_unknown_packet(self, data):
        """Provide detailed analysis of unknown packets"""
        analysis = {
            'length': len(data),
            'first_byte': f"0x{data[0]:02X}",
            'rorg_type': self._get_rorg_type(data[0]),
            'potential_eep': self._guess_eep_from_data(data),
            'hex_dump': data.hex(' ', 1)
        }
        return analysis

    def _get_rorg_type(self, rorg):
        """Map RORG byte to known types"""
        rorg_types = {
            0xA5: "4BS (4-byte communication)",
            0xD2: "VLD (variable length data)",
            0xF6: "RPS (repeater)",
            0xD5: "1BS (1-byte communication)",
            0xA7: "Smart Ack",
            0x30: "Secure Device",
            0xD4: "UTE (universal teach-in)"
        }
        return rorg_types.get(rorg, "Unknown RORG")

    def _guess_eep_from_data(self, data):
        """Attempt to guess EEP from data pattern"""
        if len(data) < 2:
            return "Unknown (data too short)"

        rorg = data[0]
        if rorg == 0xA5 and len(data) >= 5:
            return f"A5-{data[3]:02X}-{data[4]:02X}"
        elif rorg == 0xD2 and len(data) >= 4:
            return f"D2-{data[1]:02X}-{data[2]:02X}"
        elif rorg == 0xF6:
            return "F6-02-01/02 (Rocker switch)"
        elif rorg == 0xD5:
            return "D5-00-01 (Contact sensor)"
        return "Unknown (pattern not recognized)"
    def _decode_d2(self, payload):
        """Decode VLD - D2 profiles with proper EEP implementations"""
        if len(payload) < 4:
            return {'type': 'vld', 'error': 'short_payload'}

        # First try EEP-specific decoders
        eep_decoders = [
            self._decode_d2_14_41,  # Multi-sensor (temp/humidity/accel/magnet)
            self._decode_d2_14_40,  # Multi-sensor (temp/humidity/accel)
            self._decode_d2_01_12,  # Temperature/humidity sensor
        ]

        for decoder in eep_decoders:
            try:
                result = decoder(payload)
                if result and result.get('type') != 'unknown':
                    return result
            except Exception as e:
                if DEBUG:
                    print(f"EEP decoder {decoder.__name__} failed: {e}")
                continue

        # Fallback to pattern matching for unknown sensors
        fallback_patterns = [
            self._pattern_d2_standard,
            self._pattern_d2_alt1,
            self._pattern_d2_alt2
        ]

        for pattern in fallback_patterns:
            try:
                result = pattern(payload)
                if result:
                    return result
            except Exception as e:
                if DEBUG:
                    print(f"Pattern {pattern.__name__} failed: {e}")
                continue

        # If nothing works, provide detailed analysis
        return {
            'type': 'vld',
            'raw': payload.hex().upper(),
            'bytes': [f"0x{b:02X}({b})" for b in payload[:12]],
            'analysis': self._analyze_vld_payload(payload),
            'eep_analysis': self._analyze_eep_candidates(payload)
        }

    def _decode_d2_14_41(self, payload):
        """Decode D2-14-41: Multi-sensor with temp/humidity/illumination/acceleration/magnet"""
        if len(payload) < 9:
            return None

        try:
            # D2-14-41 bit layout (9 bytes):
            # Temperature: 10 bits (bits 0-9)
            # Humidity: 8 bits (bits 10-17)
            # Illumination: 17 bits (bits 18-34)
            # Acceleration X: 10 bits (bits 35-44)
            # Acceleration Y: 10 bits (bits 45-54)
            # Acceleration Z: 10 bits (bits 55-64)
            # Acceleration Status: 2 bits (bits 65-66)
            # Magnet Contact: 1 bit (bit 67)

            # Convert payload to bit array for easier extraction
            bit_data = 0
            for i, byte in enumerate(payload[:9]):
                bit_data |= (byte << (8 * (8 - i)))

            # Extract fields (bit positions from left/MSB)
            temp_raw = (bit_data >> 62) & 0x3FF  # 10 bits for temperature
            humidity_raw = (bit_data >> 54) & 0xFF  # 8 bits for humidity
            illumination_raw = (bit_data >> 37) & 0x1FFFF  # 17 bits for illumination
            accel_x_raw = (bit_data >> 27) & 0x3FF  # 10 bits for accel X
            accel_y_raw = (bit_data >> 17) & 0x3FF  # 10 bits for accel Y
            accel_z_raw = (bit_data >> 7) & 0x3FF  # 10 bits for accel Z
            accel_status = (bit_data >> 5) & 0x03  # 2 bits for accel status
            magnet_contact = (bit_data >> 4) & 0x01  # 1 bit for magnet

            # Apply scaling according to D2-14-41 specification
            temperature_c = -40.0 + (temp_raw * 100.0 / 1023.0)  # -40°C to +60°C
            humidity_percent = humidity_raw * 100.0 / 255.0  # 0% to 100%
            illumination_lx = illumination_raw * 100000.0 / 131071.0  # 0 to 100000 lx

            # Acceleration: ±2.5g range
            accel_x_g = ((accel_x_raw - 512) * 5.0) / 1023.0
            accel_y_g = ((accel_y_raw - 512) * 5.0) / 1023.0
            accel_z_g = ((accel_z_raw - 512) * 5.0) / 1023.0

            # Sanity check ranges
            if not (-50 <= temperature_c <= 70):
                return None
            if not (0 <= humidity_percent <= 105):
                return None

            result = {
                'type': 'multi_sensor',
                'temperature_c': round(temperature_c, 2),
                'temperature_f': round(temperature_c * 9 / 5 + 32, 2),
                'humidity_percent': round(humidity_percent, 1),
                'illumination_lx': round(illumination_lx, 0),
                'acceleration_x_g': round(accel_x_g, 3),
                'acceleration_y_g': round(accel_y_g, 3),
                'acceleration_z_g': round(accel_z_g, 3),
                'acceleration_status': accel_status,
                'magnet_contact': 'open' if magnet_contact else 'closed',
                'eep_profile': 'D2-14-41',
                'debug_raw_values': {
                    'temp_raw': temp_raw,
                    'humidity_raw': humidity_raw,
                    'illumination_raw': illumination_raw,
                    'accel_x_raw': accel_x_raw,
                    'accel_y_raw': accel_y_raw,
                    'accel_z_raw': accel_z_raw,
                    'magnet_raw': magnet_contact
                }
            }

            return result

        except Exception as e:
            if DEBUG:
                print(f"D2-14-41 decode error: {e}")
            return None

    def _decode_d2_14_40(self, payload):
        """Decode D2-14-40: Multi-sensor without magnet contact"""
        if len(payload) < 9:
            return None

        # Same as D2-14-41 but without magnet contact bit
        result = self._decode_d2_14_41(payload)
        if result:
            result['eep_profile'] = 'D2-14-40'
            # Remove magnet contact for this profile
            if 'magnet_contact' in result:
                del result['magnet_contact']
        return result

    def _decode_d2_01_12(self, payload):
        """Decode D2-01-12: Temperature and humidity sensor"""
        if len(payload) < 4:
            return None

        try:
            # D2-01-12 simpler format - just temp and humidity
            # Temperature: typically in first 2 bytes
            # Humidity: typically in next byte

            temp_raw = (payload[0] << 8) | payload[1]
            humidity_raw = payload[2] if len(payload) > 2 else 0

            # Try different scaling approaches
            scalings = [
                # (temp_offset, temp_scale, hum_scale, temp_range)
                (-40, 100 / 1023, 100 / 255, (-50, 70)),
                (-273.15, 0.1, 1, (-50, 70)),
                (0, 0.01, 0.4, (-50, 70)),
                (-2000, 0.01, 1, (-50, 70))
            ]

            for temp_offset, temp_scale, hum_scale, temp_range in scalings:
                temp_c = temp_offset + (temp_raw * temp_scale)
                humidity_percent = humidity_raw * hum_scale

                if temp_range[0] <= temp_c <= temp_range[1] and 0 <= humidity_percent <= 100:
                    return {
                        'type': 'temp_humidity',
                        'temperature_c': round(temp_c, 2),
                        'temperature_f': round(temp_c * 9 / 5 + 32, 2),
                        'humidity_percent': round(humidity_percent, 1),
                        'eep_profile': 'D2-01-12',
                        'debug_raw_values': {
                            'temp_raw': temp_raw,
                            'humidity_raw': humidity_raw,
                            'scaling_used': f"offset={temp_offset}, scale={temp_scale}"
                        }
                    }
        except:
            pass

        return None

    def _analyze_eep_candidates(self, payload):
        """Analyze payload for different EEP profile candidates"""
        if len(payload) < 4:
            return {}

        analysis = {
            'payload_length': len(payload),
            'possible_eep_profiles': [],
            'temperature_candidates': [],
            'humidity_candidates': []
        }

        # Test D2-14-41 style extraction with different bit positions
        if len(payload) >= 9:
            for temp_start_bit in range(0, 16, 2):  # Try different starting positions
                try:
                    bit_data = 0
                    for i, byte in enumerate(payload[:9]):
                        bit_data |= (byte << (8 * (8 - i)))

                    temp_raw = (bit_data >> (72 - temp_start_bit - 10)) & 0x3FF
                    temp_c = -40.0 + (temp_raw * 100.0 / 1023.0)

                    if -50 <= temp_c <= 70:
                        analysis['temperature_candidates'].append({
                            'start_bit': temp_start_bit,
                            'raw_value': temp_raw,
                            'temperature_c': round(temp_c, 2),
                            'method': 'D2-14-41_style'
                        })
                except:
                    pass

        # Test simple 2-byte temperature patterns
        for i in range(len(payload) - 1):
            temp_raw_be = (payload[i] << 8) | payload[i + 1]
            temp_raw_le = payload[i] | (payload[i + 1] << 8)

            for raw_val, endian in [(temp_raw_be, 'BE'), (temp_raw_le, 'LE')]:
                for offset, scale in [(-40, 100 / 1023), (-273.15, 0.1), (0, 0.01), (-2000, 0.01)]:
                    temp_c = offset + (raw_val * scale)
                    if -50 <= temp_c <= 70:
                        analysis['temperature_candidates'].append({
                            'bytes': f"{i}-{i + 1}",
                            'endian': endian,
                            'raw_value': raw_val,
                            'temperature_c': round(temp_c, 2),
                            'scaling': f"offset={offset}, scale={scale}",
                            'method': 'simple_2byte'
                        })

        return analysis

    def _pattern_d2_standard(self, payload):
        """Standard VLD temp/humidity pattern"""
        if len(payload) < 4:
            return None

        temp_raw = (payload[1] << 8) | payload[2]
        humidity = payload[3]

        temp_c = (temp_raw - 1000) / 10.0

        if -40 <= temp_c <= 80 and 0 <= humidity <= 100:
            return {
                'type': 'temp_humidity',
                'temperature_c': round(temp_c, 1),
                'temperature_f': round(temp_c * 9 / 5 + 32, 1),
                'humidity_percent': humidity,
                'pattern': 'vld_standard'
            }
        return None

    def _pattern_d2_alt1(self, payload):
        """Alternative VLD pattern 1"""
        if len(payload) < 6:
            return None

        temp_raw = (payload[2] << 8) | payload[3]
        humidity = payload[4]

        temp_c = temp_raw / 100.0

        if -40 <= temp_c <= 80 and 0 <= humidity <= 100:
            return {
                'type': 'temp_humidity',
                'temperature_c': round(temp_c, 1),
                'temperature_f': round(temp_c * 9 / 5 + 32, 1),
                'humidity_percent': humidity,
                'pattern': 'vld_alt1'
            }
        return None

    def _pattern_d2_alt2(self, payload):
        """Alternative VLD pattern 2"""
        if len(payload) < 6:
            return None

        temp_raw = payload[1] | (payload[2] << 8)
        humidity = payload[3]

        temp_c = (temp_raw - 2000) / 10.0

        if -40 <= temp_c <= 80 and 0 <= humidity <= 100:
            return {
                'type': 'temp_humidity',
                'temperature_c': round(temp_c, 1),
                'temperature_f': round(temp_c * 9 / 5 + 32, 1),
                'humidity_percent': humidity,
                'pattern': 'vld_alt2'
            }
        return None

    def _analyze_vld_payload(self, payload):
        """Analyze VLD payload to help identify the pattern"""
        analysis = {'possible_temps': [], 'possible_humidity': []}

        if len(payload) >= 4:
            for i in range(len(payload) - 1):
                val16_be = (payload[i] << 8) | payload[i + 1]
                val16_le = payload[i] | (payload[i + 1] << 8)

                for val, endian in [(val16_be, 'BE'), (val16_le, 'LE')]:
                    for offset, scale in [(-2000, 10), (-1000, 10), (0, 100), (-20 * 100, 100)]:
                        temp_c = (val + offset) / scale
                        if -50 <= temp_c <= 100:
                            analysis['possible_temps'].append({
                                'bytes': f"{i}-{i + 1}({endian})",
                                'temp_c': round(temp_c, 1),
                                'raw': val,
                                'formula': f"({val}+{offset})/{scale}"
                            })

                if 0 <= payload[i] <= 100:
                    analysis['possible_humidity'].append({
                        'byte': i,
                        'value': payload[i]
                    })

        return analysis

    def _decode_a5(self, payload):
        """Decode 4BS - temperature/humidity sensors"""
        if len(payload) < 4:
            return {'type': '4bs', 'error': 'short_payload'}

        db3, db2, db1, db0 = payload[:4]
        learn_bit = (db0 & 0x08) == 0

        if learn_bit:
            return {'type': 'teach_in', 'eep_data': f"{db3:02X}{db2:02X}{db1:02X}"}

        # Try A5-07-02 (temp/humidity)
        try:
            humidity = db2 * 100.0 / 250.0
            temp_c = -20.0 + (db1 * 60.0 / 250.0)

            if -40 <= temp_c <= 80 and 0 <= humidity <= 100:
                return {
                    'type': 'temp_humidity',
                    'temperature_c': round(temp_c, 1),
                    'temperature_f': round(temp_c * 9 / 5 + 32, 1),
                    'humidity_percent': round(humidity, 1),
                    'pattern': 'a5_07_02'
                }
        except:
            pass

        return {'type': '4bs', 'raw': f"{db3:02X}{db2:02X}{db1:02X}{db0:02X}"}

    def _decode_f6(self, payload):
        """Decode RPS - switches/buttons with detailed button identification"""
        if not payload:
            return {'type': 'switch', 'state': 'no_button', 'action': 'released'}

        data_byte = payload[0]

        # Get button information
        button_info = self._decode_button_combination(data_byte)

        result = {
            'type': 'switch',
            'pressed': bool(data_byte & 0x10),  # Energy bow bit
            'raw_data': f"0x{data_byte:02X}",
            'button_combination': button_info['combination'],
            'button_name': button_info['name'],
            'button_description': button_info['description'],
            'action': 'pressed' if bool(data_byte & 0x10) else 'released'
        }

        # Add individual button states
        if 'button_a' in button_info:
            result['button_a_pressed'] = button_info['button_a']
        if 'button_b' in button_info:
            result['button_b_pressed'] = button_info['button_b']
        if 'button_c' in button_info:
            result['button_c_pressed'] = button_info['button_c']
        if 'button_d' in button_info:
            result['button_d_pressed'] = button_info['button_d']
        if 'raw_bits' in button_info:
            result['raw_bits'] = button_info['raw_bits']

        return result

    def _decode_button_combination(self, data_byte):
        """Decode specific button combination for your 4-button switch"""
        # Your switch patterns (based on observed data):
        # Button A: 0x30 = 00110000 (Left Top)
        # Button B: 0x70 = 01110000 (Right Top)
        # Button C: 0x50 = 01010000 (Left Bottom or Right Bottom)
        # Button D: Need to identify the 4th pattern
        # Released: 0x00 = 00000000 (all buttons released)

        energy_bow = bool(data_byte & 0x10)  # Bit 4 (energy bow - indicates press)
        bit5 = bool(data_byte & 0x20)  # Bit 5
        bit6 = bool(data_byte & 0x40)  # Bit 6
        bit7 = bool(data_byte & 0x80)  # Bit 7

        # Define button mappings based on your actual patterns
        button_patterns = {
            0x30: {
                'combination': 'button_a_press',
                'name': 'button_a',
                'description': 'Button A  pressed',
                'button_a': True, 'button_b': False, 'button_c': False, 'button_d': False
            },
            0x70: {
                'combination': 'button_b_press',
                'name': 'button_b',
                'description': 'Button B  pressed',
                'button_a': False, 'button_b': True, 'button_c': False, 'button_d': False
            },
            0x50: {
                'combination': 'button_c_press',
                'name': 'button_c',
                'description': 'Button C  pressed',
                'button_a': False, 'button_b': False, 'button_c': True, 'button_d': False
            },
            0x10: {  # Potential 4th button pattern
                'combination': 'button_d_press',
                'name': 'button_d',
                'description': 'Button D  pressed',
                'button_a': False, 'button_b': False, 'button_c': False, 'button_d': True
            },
            0xB0: {  # Alternative 4th button pattern
                'combination': 'button_d_press',
                'name': 'button_d',
                'description': 'Button D  pressed',
                'button_a': False, 'button_b': False, 'button_c': False, 'button_d': True
            },
            0xF0: {  # Alternative 4th button pattern
                'combination': 'button_d_press',
                'name': 'button_d',
                'description': 'Button D (Bottom Right) pressed',
                'button_a': False, 'button_b': False, 'button_c': False, 'button_d': True
            },
            0x00: {
                'combination': 'released',
                'name': 'released',
                'description': 'All buttons released',
                'button_a': False, 'button_b': False, 'button_c': False, 'button_d': False
            }
        }

        # Check for known patterns first
        if data_byte in button_patterns:
            pattern = button_patterns[data_byte]
            result = {
                'combination': pattern['combination'],
                'name': pattern['name'],
                'description': pattern['description'],
                'button_a': pattern['button_a'],
                'button_b': pattern['button_b'],
                'button_c': pattern['button_c'],
                'button_d': pattern['button_d'],
                'raw_bits': {
                    'energy_bow': energy_bow,
                    'bit7': bit7,
                    'bit6': bit6,
                    'bit5': bit5,
                    'data_byte': f"0x{data_byte:02X}",
                    'binary': f"{data_byte:08b}"
                }
            }
            return result

        # Handle unknown patterns - try to guess which button based on bit patterns
        # Standard rocker switch encoding uses bits 5-6 for rocker ID
        rocker_bits = (data_byte >> 5) & 0x03  # Extract bits 6-5

        # Map rocker patterns to buttons
        rocker_map = {
            0: {'name': 'none', 'desc': 'No button', 'buttons': [False, False, False, False]},
            1: {'name': 'button_a', 'desc': 'Button A (inferred)', 'buttons': [True, False, False, False]},
            2: {'name': 'button_c', 'desc': 'Button C (inferred)', 'buttons': [False, False, True, False]},
            3: {'name': 'button_b', 'desc': 'Button B (inferred)', 'buttons': [False, True, False, False]}
        }

        if rocker_bits in rocker_map and energy_bow:
            mapping = rocker_map[rocker_bits]
            return {
                'combination': f'{mapping["name"]}_press_inferred',
                'name': mapping['name'],
                'description': f'{mapping["desc"]} from pattern 0x{data_byte:02X}',
                'button_a': mapping['buttons'][0],
                'button_b': mapping['buttons'][1],
                'button_c': mapping['buttons'][2],
                'button_d': mapping['buttons'][3],
                'raw_bits': {
                    'energy_bow': energy_bow,
                    'bit7': bit7,
                    'bit6': bit6,
                    'bit5': bit5,
                    'rocker_id': rocker_bits,
                    'data_byte': f"0x{data_byte:02X}",
                    'binary': f"{data_byte:08b}",
                    'inference': f'Rocker bits {rocker_bits} + energy_bow'
                }
            }

        # Complete unknown pattern
        return {
            'combination': f'unknown_0x{data_byte:02X}',
            'name': 'unknown',
            'description': f'Unknown button pattern: 0x{data_byte:02X}',
            'button_a': False,
            'button_b': False,
            'button_c': False,
            'button_d': False,
            'raw_bits': {
                'energy_bow': energy_bow,
                'bit7': bit7,
                'bit6': bit6,
                'bit5': bit5,
                'rocker_id': rocker_bits,
                'data_byte': f"0x{data_byte:02X}",
                'binary': f"{data_byte:08b}",
                'need_mapping': True
            }
        }

    def _decode_d4(self, payload):
        """Decode Universal Teach-In"""
        if len(payload) < 7:
            return {'type': 'teach_in', 'error': 'short_payload'}

        return {
            'type': 'teach_in',
            'eep_profile': f"{payload[4]:02X}-{payload[5]:02X}-{payload[6]:02X}",
            'manufacturer': f"0x{payload[6]:02X}"
        }

    def _get_signal_quality(self, status):
        """Get signal quality from status byte"""
        rssi = status & 0x0F if isinstance(status, int) else 0
        quality = 'excellent' if rssi > 12 else 'good' if rssi > 8 else 'fair' if rssi > 4 else 'poor'
        return {'rssi': rssi, 'quality': quality}

    def publish_data(self, data):
        """Publish sensor data to MQTT"""
        if not self.mqtt_client or not data:
            return

        try:
            device_id = data['device_id'].replace(':', '')

            # Publish complete data
            topic = f"{MQTT_TOPIC}/{device_id}"
            self.mqtt_client.publish(topic, json.dumps(data))

            # Publish individual metrics for Telegraf for further usage
            if data.get('type') == 'multi_sensor':
                metrics = {
                    'device_id': data['device_id'],
                    'timestamp': data['timestamp'],
                    'rorg': data['rorg'],
                    'signal_quality_rssi': data['signal_quality']['rssi'],
                    'signal_quality_quality': data['signal_quality']['quality'],
                    'type': data['type'],
                    'temperature_c': data['temperature_c'],
                    'temperature_f': data['temperature_f'],
                    'humidity_percent': data['humidity_percent'],
                    'illumination_lx': data['illumination_lx'],
                    'acceleration_x_g': data['acceleration_x_g'],
                    'acceleration_y_g': data['acceleration_y_g'],
                    'acceleration_z_g': data['acceleration_z_g'],
                    'acceleration_status': data['acceleration_status'],
                    'magnet_contact': data['magnet_contact'],
                    'eep_profile': data['eep_profile'],
                }
            # self.mqtt_client.publish(f"{MQTT_TOPIC}/metrics/{device_id}",json.dumps(metrics))

            elif data.get('type') == 'switch':

                metrics = {
                    'button_pressed': 1 if data.get('pressed') else 0,
                    'button_combination': data.get('button_combination', 'none'),
                    'button_name': data.get('button_name', 'unknown'),
                    'device_id': device_id,
                    'timestamp': data['timestamp']
                }

                # Add individual button states
                if 'button_a_pressed' in data:
                    metrics['button_a_pressed'] = 1 if data['button_a_pressed'] else 0
                if 'button_b_pressed' in data:
                    metrics['button_b_pressed'] = 1 if data['button_b_pressed'] else 0
                if 'button_c_pressed' in data:
                    metrics['button_c_pressed'] = 1 if data['button_c_pressed'] else 0
                if 'button_d_pressed' in data:
                    metrics['button_d_pressed'] = 1 if data['button_d_pressed'] else 0
                # self.mqtt_client.publish(f"{MQTT_TOPIC}/metrics/{device_id}",json.dumps(metrics))

            if DEBUG:
                print(f"📤 Published: {device_id} -> {data.get('type', 'unknown')}")

        except Exception as e:
            if DEBUG:
                print(f"Publish error: {e}")

    def run(self):
        """Main run loop"""
        if not self.connect_serial():
            return False

        self.connect_mqtt()

        print(f"🚀 EnOcean Gateway started")
        print(f"   Serial: {PORT}@{BAUD_RATE}")
        print(f"   MQTT: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"   Topic: {MQTT_TOPIC}")
        print(f"   Debug: {DEBUG}")

        self.running = True
        read_thread = threading.Thread(target=self.read_packets, daemon=True)
        read_thread.start()

        packet_count = 0
        try:
            while True:
                if not self.packet_queue.empty():
                    packet = self.packet_queue.get()
                    decoded = self.decode_packet(packet)

                    if decoded:
                        packet_count += 1
                        self.publish_data(decoded)

                        if DEBUG or decoded.get('type') in ['temp_humidity', 'switch']:
                            print(f"📦 {packet_count}: {decoded['device_id']} -> {decoded.get('type', 'unknown')}")
                            if 'temperature_c' in decoded:
                                pattern = decoded.get('eep_profile', decoded.get('pattern', 'unknown'))
                                temp_c = decoded['temperature_c']
                                humidity = decoded.get('humidity_percent', 'N/A')
                                print(f"    🌡️  {temp_c}°C, 💧 {humidity}% [{pattern}]")

                                # Show additional sensor data if available
                                if 'illumination_lx' in decoded:
                                    print(f"    💡 Illumination: {decoded['illumination_lx']} lx")
                                if 'magnet_contact' in decoded:
                                    print(f"    🚪 Magnet: {decoded['magnet_contact']}")
                                if 'acceleration_x_g' in decoded:
                                    x, y, z = decoded['acceleration_x_g'], decoded['acceleration_y_g'], decoded[
                                        'acceleration_z_g']
                                    print(f"    📐 Acceleration: X={x}g, Y={y}g, Z={z}g")

                                # Show debug info in debug mode
                                if DEBUG and 'debug_raw_values' in decoded:
                                    debug = decoded['debug_raw_values']
                                    print(
                                        f"    🔍 Raw values: temp={debug.get('temp_raw')}, hum={debug.get('humidity_raw')}")
                            elif 'pressed' in decoded:
                                action = "PRESSED" if decoded['pressed'] else "RELEASED"
                                button_desc = decoded.get('button_description', 'Unknown button')
                                button_name = decoded.get('button_name', 'unknown')
                                raw_data = decoded.get('raw_data', 'N/A')
                                print(f"    🔘 {action}: {button_desc}")
                                print(f"       Button: {button_name} | Raw: {raw_data}")

                                if 'button_a_pressed' in decoded or 'button_b_pressed' in decoded or 'button_c_pressed' in decoded or 'button_d_pressed' in decoded:
                                    a_state = "A✓" if decoded.get('button_a_pressed') else "A○"
                                    b_state = "B✓" if decoded.get('button_b_pressed') else "B○"
                                    c_state = "C✓" if decoded.get('button_c_pressed') else "C○"
                                    d_state = "D✓" if decoded.get('button_d_pressed') else "D○"
                                    print(f"       Individual buttons: {a_state} {b_state} {c_state} {d_state}")
                            elif decoded.get('type') == 'vld' and ('analysis' in decoded or 'eep_analysis' in decoded):
                                print(f"    🔍 VLD Analysis for {decoded.get('raw', 'N/A')}:")

                                if 'eep_analysis' in decoded:
                                    eep_analysis = decoded['eep_analysis']
                                    print(f"        📋 Payload length: {eep_analysis.get('payload_length')} bytes")

                                    if eep_analysis.get('temperature_candidates'):
                                        print(f"        🌡️  Temperature candidates:")
                                        for i, candidate in enumerate(eep_analysis['temperature_candidates'][:5]):
                                            method = candidate.get('method', 'unknown')
                                            temp = candidate.get('temperature_c')
                                            if method == 'D2-14-41_style':
                                                print(
                                                    f"          {i + 1}. {temp}°C [D2-14-41 bit {candidate['start_bit']}]")
                                            else:
                                                bytes_info = candidate.get('bytes', 'N/A')
                                                endian = candidate.get('endian', '')
                                                scaling = candidate.get('scaling', '')
                                                print(
                                                    f"          {i + 1}. {temp}°C [bytes {bytes_info} {endian}, {scaling}]")

                                if 'analysis' in decoded and decoded['analysis']['possible_temps']:
                                    print(f"        🔍 Legacy analysis:")
                                    for temp in decoded['analysis']['possible_temps'][:3]:
                                        print(
                                            f"          Bytes {temp['bytes']}: {temp['temp_c']}°C [{temp['formula']}]")

                                if decoded.get('bytes'):
                                    print(f"        📊 Raw bytes: {' '.join(decoded['bytes'][:8])}")

                else:
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        finally:
            self.running = False
            if self.serial_conn:
                self.serial_conn.close()
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()


if __name__ == "__main__":
    gateway = EnOceanGateway()
    gateway.run()