# src/protocol/eep_profiles.py
"""
EnOcean Equipment Profile (EEP) decoders for different device types
Fixed version with step-by-step implementation
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from ..utils.logger import Logger


class BaseEEPDecoder(ABC):
    """Base class for EEP decoders"""

    def __init__(self, logger: Logger):
        self.logger = logger

    @abstractmethod
    def can_decode(self, data: bytes) -> bool:
        """Check if this decoder can handle the data"""
        pass

    @abstractmethod
    def decode(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode the data"""
        pass


class RPSDecoder(BaseEEPDecoder):
    """Decoder for Rocker Switch (F6) profiles """

    def can_decode(self, data: bytes) -> bool:
        return len(data) > 0 and data[0] == 0xF6

    def decode(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode RPS packets"""
        payload = data[1:2] if len(data) > 1 else []

        if not payload:
            return {
                'type': 'switch',
                'state': 'no_button',
                'action': 'released',
                'pressed': False,
                'raw_data': '0x00'
            }

        data_byte = payload[0]
        button_info = self._decode_button_combination(data_byte)

        # Base result structure
        result = {
            'type': 'switch',
            'pressed': bool(data_byte & 0x10),  # Energy bow bit
            'raw_data': f"0x{data_byte:02X}",
            'action': 'pressed' if bool(data_byte & 0x10) else 'released'
        }

        # Add button information
        result.update(button_info)

        return result

    def _decode_button_combination(self, data_byte: int) -> Dict[str, Any]:
        """Decode button combinations - FIXED VERSION"""

        # Extract bits for analysis
        energy_bow = bool(data_byte & 0x10)  # Bit 4
        bit5 = bool(data_byte & 0x20)
        bit6 = bool(data_byte & 0x40)
        bit7 = bool(data_byte & 0x80)

        # Known button patterns from your original code
        if data_byte == 0x30:
            return {
                'button_combination': 'button_a_press',
                'button_name': 'button_a',
                'button_description': 'Button A pressed',
                'button_a_pressed': True,
                'button_b_pressed': False,
                'button_c_pressed': False,
                'button_d_pressed': False
            }
        elif data_byte == 0x70:
            return {
                'button_combination': 'button_b_press',
                'button_name': 'button_b',
                'button_description': 'Button B pressed',
                'button_a_pressed': False,
                'button_b_pressed': True,
                'button_c_pressed': False,
                'button_d_pressed': False
            }
        elif data_byte == 0x50:
            return {
                'button_combination': 'button_c_press',
                'button_name': 'button_c',
                'button_description': 'Button C pressed',
                'button_a_pressed': False,
                'button_b_pressed': False,
                'button_c_pressed': True,
                'button_d_pressed': False
            }
        elif data_byte in [0x10, 0xB0, 0xF0]:  # Multiple patterns for button D
            return {
                'button_combination': 'button_d_press',
                'button_name': 'button_d',
                'button_description': 'Button D pressed',
                'button_a_pressed': False,
                'button_b_pressed': False,
                'button_c_pressed': False,
                'button_d_pressed': True
            }
        elif data_byte == 0x00:
            return {
                'button_combination': 'released',
                'button_name': 'released',
                'button_description': 'All buttons released',
                'button_a_pressed': False,
                'button_b_pressed': False,
                'button_c_pressed': False,
                'button_d_pressed': False
            }
        else:
            # Unknown pattern
            rocker_bits = (data_byte >> 5) & 0x03
            return {
                'button_combination': f'unknown_0x{data_byte:02X}',
                'button_name': 'unknown',
                'button_description': f'Unknown button pattern: 0x{data_byte:02X}',
                'button_a_pressed': False,
                'button_b_pressed': False,
                'button_c_pressed': False,
                'button_d_pressed': False,
                'raw_bits': {
                    'energy_bow': energy_bow,
                    'bit7': bit7,
                    'bit6': bit6,
                    'bit5': bit5,
                    'rocker_id': rocker_bits,
                    'data_byte': f"0x{data_byte:02X}",
                    'binary': f"{data_byte:08b}"
                }
            }


class FourBSDecoder(BaseEEPDecoder):
    """Decoder for 4-Byte Sensor (A5) profiles - STEP 2"""

    def can_decode(self, data: bytes) -> bool:
        return len(data) > 0 and data[0] == 0xA5

    def decode(self, data: bytes) -> Optional[Dict[str, Any]]:
        # The parser now provides only the EEP data payload (RORG + 4 bytes)
        print(f"data leng {len(data)}")
        if len(data) != 5:
            self.logger.warning(f"FourBSDecoder received incorrect data length: {len(data)}")
            return None

        db3, db2, db1, db0 = data[1:5]
        self.logger.debug(f"[FourBSDecoder] Received: DB3={db3:02X}, DB2={db2:02X}, DB1={db1:02X}, DB0={db0:02X}")

        # Check for teach-in packet FIRST
        if (db0 & 0x08) == 0:
            return {
                'type': 'teach_in',
                'eep_profile_guess': f"A5-{db3:02X}-{db2:02X}",
                'raw_data': data[1:].hex()
            }

        decoding_functions = [
            self._decode_a5_12_01, self._decode_a5_12_02, self._decode_a5_09_01,
            self._decode_a5_10_01, self._decode_a5_02_01, self._decode_a5_02_02,
            self._decode_a5_10_02, self._decode_a5_09_04, self._decode_a5_06_01,
            self._decode_a5_07_01, self._decode_a5_12_03, self._decode_a5_13_01,
            self._decode_a5_10_09, self._decode_a5_07_02, self._decode_a5_02_04,
            self._decode_a5_04_02, self._decode_a5_02_05, self._decode_a5_10_03,
            self._decode_a5_10_11, self._decode_a5_04_01,
        ]

        for func in decoding_functions:
            result = func(db3, db2, db1, db0)
            if result:
                return result  # Return the first successful match

        # Return raw data if no pattern matches
        return {
            'type': '4bs',
            'raw_data': f"{db3:02X}{db2:02X}{db1:02X}{db0:02X}",
            'learn_bit': False
        }

    def _decode_a5_04_01(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        """A5-04-01: Temp (0-40C) + Humidity (0-100%)."""
        if db3 != 0x00: return None
        temp_c = db1 * 40.0 / 250.0
        humidity = db2 * 100.0 / 250.0
        if 0 <= temp_c <= 40 and 0 <= humidity <= 100:
            return {'type': 'temp_humidity', 'temperature_c': round(temp_c, 1),
                    'humidity_percent': round(humidity, 1), 'eep_profile': 'A5-04-01'}
        return None

    def _decode_a5_02_01(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db2 != 0x00: return None
        temp_c = 40.0 - (db3 * 80.0 / 255.0)
        if -40 <= temp_c <= 40: return {'type': 'temperature_sensor', 'temperature_c': round(temp_c, 1),
                                        'eep_profile': 'A5-02-01'}
        return None

    def _decode_a5_02_02(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db2 != 0x00: return None
        temp_c = 40.0 - (db3 * 40.0 / 255.0)
        if 0 <= temp_c <= 40: return {'type': 'temperature_sensor', 'temperature_c': round(temp_c, 1),
                                      'eep_profile': 'A5-02-02'}
        return None

    def _decode_a5_10_01(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db3 != 0x00: return None
        humidity = db2 * 100.0 / 250.0
        if 0 <= humidity <= 100: return {'type': 'humidity_sensor', 'humidity_percent': round(humidity, 1),
                                         'eep_profile': 'A5-10-01'}
        return None

    def _decode_a5_09_04(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db3 != 0x00: return None
        co2 = db2 * 2500.0 / 255.0
        return {'type': 'co2_sensor', 'co2_ppm': round(co2), 'eep_profile': 'A5-09-04'}

    def _decode_a5_10_02(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db3 != 0x00: return None
        pressure = 500 + (db2 * 615.0 / 255.0)
        return {'type': 'barometric_sensor', 'pressure_hpa': round(pressure), 'eep_profile': 'A5-10-02'}

    def _decode_a5_06_01(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db2 != 0x00: return None
        lux = db3 * 1000.0 / 255.0
        return {'type': 'light_sensor', 'illuminance_lx': round(lux), 'eep_profile': 'A5-06-01'}

    def _decode_a5_07_01(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db2 != 0x00 or db3 != 0x00: return None
        motion = (db1 & 0x80) != 0
        return {'type': 'motion_sensor', 'motion_detected': motion, 'eep_profile': 'A5-07-01'}

    def _decode_a5_02_04(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db2 != 0x00: return None
        temp_c = -40 + (db1 * 80.0 / 255.0)
        lux = db3 * 1000.0 / 255.0
        return {'type': 'temp_illuminance_sensor', 'temperature_c': round(temp_c, 1), 'illuminance_lx': round(lux),
                'eep_profile': 'A5-02-04'}

    def _decode_a5_07_02(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db3 != 0x00: return None
        motion = (db1 & 0x80) != 0
        temp_c = db2 * 50.0 / 255.0
        if 0 <= temp_c <= 50:
            return {'type': 'motion_temp_sensor', 'motion_detected': motion, 'temperature_c': round(temp_c, 1),
                    'eep_profile': 'A5-07-02'}
        return None

    def _decode_a5_02_05(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        temp_c = -40 + (db1 * 80.0 / 255.0)
        lux = db2 * 1000.0 / 255.0
        humidity = db3 * 100.0 / 255.0
        return {'type': 'temp_humidity_illuminance_sensor', 'temperature_c': round(temp_c, 1),
                'illuminance_lx': round(lux), 'humidity_percent': round(humidity, 1), 'eep_profile': 'A5-02-05'}

    def _decode_a5_10_03(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        temp_c = db3 * 40.0 / 255.0
        humidity = db2 * 100.0 / 255.0
        pressure = 500 + (db1 * 615.0 / 255.0)
        return {'type': 'temp_humidity_barometric_sensor', 'temperature_c': round(temp_c, 1),
                'humidity_percent': round(humidity, 1), 'pressure_hpa': round(pressure), 'eep_profile': 'A5-10-03'}

    def _decode_a5_10_11(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        temp_c = -40 + (db1 * 120.0 / 255.0)
        humidity = db2 * 100.0 / 255.0
        pressure = 500 + (db3 * 615.0 / 255.0)
        return {'type': 'temp_humidity_barometric_sensor', 'temperature_c': round(temp_c, 1),
                'humidity_percent': round(humidity, 1), 'pressure_hpa': round(pressure), 'eep_profile': 'A5-10-11'}

    def _decode_a5_04_02(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        """NOTE: Using A5-08-01 for Accelerometer as it's more standard"""
        if (db0 & 0xF0) != 0x00: return None
        x = (db3 * 4.0 / 255.0) - 2.0
        y = (db2 * 4.0 / 255.0) - 2.0
        z = (db1 * 4.0 / 255.0) - 2.0
        return {'type': 'accelerometer', 'acceleration_x_g': round(x, 2), 'acceleration_y_g': round(y, 2),
                'acceleration_z_g': round(z, 2), 'eep_profile': 'A5-08-01'}

    def _decode_a5_09_01(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        """NOTE: Using A5-13-02 for Soil Moisture"""
        if db3 != 0x00 or db2 != 0x00: return None
        moisture = db1 * 100.0 / 250.0
        if 0 <= moisture <= 100: return {'type': 'soil_moisture', 'moisture_percent': round(moisture, 1),
                                         'eep_profile': 'A5-13-02'}
        return None

    def _decode_a5_10_09(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db3 != 0x00: return None
        intensity = db2 * 100.0 / 255.0
        detected = (db0 >> 4) & 0x01
        return {'type': 'rain_sensor', 'intensity_percent': round(intensity, 1), 'detected': bool(detected),
                'eep_profile': 'A5-10-09'}

    def _decode_a5_12_01(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db2 != 0x00 or db3 != 0x00: return None
        return {'type': 'smoke_detector', 'alarm': bool((db0 >> 3) & 0x01), 'eep_profile': 'A5-12-01'}

    def _decode_a5_12_02(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db2 != 0x00 or db3 != 0x00: return None
        return {'type': 'glass_break', 'alarm': bool((db0 >> 3) & 0x01), 'eep_profile': 'A5-12-02'}

    def _decode_a5_12_03(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db3 != 0x00: return None
        intensity = db2 * 100.0 / 255.0
        return {'type': 'vibration', 'intensity_percent': round(intensity, 1), 'alarm': bool((db0 >> 3) & 0x01),
                'eep_profile': 'A5-12-03'}

    def _decode_a5_13_01(self, db3, db2, db1, db0) -> Optional[Dict[str, Any]]:
        if db1 != 0x00 or db3 != 0x00: return None
        level = db2 * 100.0 / 255.0
        return {'type': 'flood_detector', 'water_level_percent': round(level, 1), 'alarm': bool((db0 >> 3) & 0x01),
                'eep_profile': 'A5-13-01'}

    # ...


class OneBSDecoder(BaseEEPDecoder):
    """Decoder for 1-Byte Sensor (D5) profiles - STEP 3"""

    def can_decode(self, data: bytes) -> bool:
        return len(data) > 0 and data[0] == 0xD5

    def decode(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode 1BS packets (contact sensors)"""
        payload = data[1:2] if len(data) > 1 else []

        if not payload:
            return {
                'type': 'contact',
                'state': 'unknown',
                'raw_data': data.hex().upper()
            }

        state_byte = payload[0]

        return {
            'type': 'contact',
            'state': 'open' if state_byte == 0x00 else 'closed',
            'raw_data': f"0x{state_byte:02X}",
            'eep_profile': 'D5-00-01'
        }


class UTEDecoder(BaseEEPDecoder):
    """Decoder for Universal Teach-In (D4) profiles - STEP 4"""

    def can_decode(self, data: bytes) -> bool:
        return len(data) > 0 and data[0] == 0xD4

    def decode(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode Universal Teach-In packets"""
        payload = data[1:]

        if len(payload) < 7:
            return {
                'type': 'teach_in',
                'error': 'short_payload',
                'raw_data': data.hex().upper()
            }

        return {
            'type': 'teach_in',
            'eep_profile': f"{payload[4]:02X}-{payload[5]:02X}-{payload[6]:02X}",
            'manufacturer': f"0x{payload[6]:02X}",
            'raw_data': payload.hex().upper()
        }


class EEPDecoder:
    """Main EEP decoder that manages all profile decoders - FIXED VERSION"""

    def __init__(self, logger: Logger):
        self.logger = logger

        # Initialize decoders in order of complexity (simple first)
        self.decoders = {
            0xF6: RPSDecoder(logger),  # Rocker switches (simple)
            0xD5: OneBSDecoder(logger),  # Contact sensors (simple)
            0xD4: UTEDecoder(logger),  # Teach-in (simple)
            0xA5: FourBSDecoder(logger),  # 4BS sensors (medium)
            0xD2: ExtendedVLDDecoder(logger)  # VLD sensors (complex)
        }

    def decode_by_rorg(self, rorg: int, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode packet data based on RORG value"""
        decoder = self.decoders.get(rorg)

        if decoder and decoder.can_decode(data):
            try:
                return decoder.decode(data)
            except Exception as e:
                self.logger.error(f"Decoder error for RORG 0x{rorg:02X}: {e}")
                return None

        # Handle other RORG types
        if rorg == 0xA7:
            return {
                'type': 'smart_ack',
                'command': data[1] if len(data) > 1 else 0,
                'raw_data': data.hex().upper()
            }
        elif rorg == 0x30:
            return {
                'type': 'secure',
                'security_level': data[1] if len(data) > 1 else 0,
                'raw_data': data.hex().upper()
            }

        return None

    def get_supported_rorg_types(self) -> List[int]:
        """Get list of supported RORG types"""
        return list(self.decoders.keys())

    def get_decoder_info(self) -> Dict[str, Any]:
        """Get information about available decoders"""
        info = {}
        for rorg, decoder in self.decoders.items():
            info[f"0x{rorg:02X}"] = {
                'decoder_class': decoder.__class__.__name__,
                'description': self._get_rorg_description(rorg)
            }
        return info

    def _get_rorg_description(self, rorg: int) -> str:
        """Get description for RORG type"""
        descriptions = {
            0xD2: "Variable Length Data (VLD) - Multi-sensor devices",
            0xA5: "4-Byte Sensor (4BS) - Temperature/humidity sensors",
            0xF6: "Rocker Switch (RPS) - Buttons and switches",
            0xD5: "1-Byte Sensor (1BS) - Contact sensors",
            0xD4: "Universal Teach-In (UTE) - Device learning"
        }
        return descriptions.get(rorg, f"Unknown RORG type 0x{rorg:02X}")


class ExtendedVLDDecoder(BaseEEPDecoder):
    """Extended VLD Decoder (D2) with full multi-sensor support"""

    def can_decode(self, data: bytes) -> bool:
        return len(data) > 0 and data[0] == 0xD2

    def decode(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode VLD packets with comprehensive EEP support"""

        if len(data) < 4:
            return {'type': 'vld', 'error': 'short_payload', 'raw_data': data.hex().upper()}

        payload = data[1:-5] if len(data) > 5 else data[1:]
        payload = data[1:]

        # Try specific EEP decoders in order of complexity
        decoders = [
            self._decode_d2_14_41,  # Multi-sensor (temp/humidity/accel/magnet)
            self._decode_d2_14_40,  # Multi-sensor without magnet
            self._decode_d2_01_12,  # Temperature/humidity sensor
            self._decode_d2_01_01,  # Electronic switch
            self._decode_d2_05_00,  # Blind control
        ]

        for decoder in decoders:
            try:
                result = decoder(payload)
                if result and result.get('type') != 'unknown':
                    return result
            except Exception as e:
                self.logger.debug(f"VLD decoder {decoder.__name__} failed: {e}")
                continue

        # If no specific EEP decoder worked, fall back to your advanced analysis
        self.logger.info("No specific VLD EEP matched, falling back to pattern matching and analysis.")
        pattern_result = self._try_pattern_matching(payload)
        if pattern_result:
            return pattern_result

        # Return comprehensive analysis if nothing works
        return {
            'type': 'unknown_vld',
            'raw_data': payload.hex().upper(),
            'analysis': self._analyze_vld_payload(payload),
            'eep_candidates': self._guess_eep_profile(payload)
        }

        # Replace this method in: enocean-gateway/src/protocol/eep_profiles.py

    def _decode_d2_14_41(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode D2-14-41: Multi-sensor with temp/humidity/illumination/acceleration/magnet"""
        if len(payload) < 9:
            return None

        try:
            # D2-14-41 uses 9-byte payload with specific bit layout
            # Convert payload to 72-bit integer for bit extraction
            bit_data = 0
            for i, byte in enumerate(payload[:9]):
                bit_data |= (byte << (8 * i))  # Little endian

            # Extract fields according to D2-14-41 specification
            # Bit positions (from LSB):
            # Temperature: bits 0-9 (10 bits)
            # Humidity: bits 10-17 (8 bits)
            # Illumination: bits 18-34 (17 bits)
            # Accel X: bits 35-44 (10 bits)
            # Accel Y: bits 45-54 (10 bits)
            # Accel Z: bits 55-64 (10 bits)
            # Accel Status: bits 65-66 (2 bits)
            # Magnet: bit 67 (1 bit)

            temp_raw = bit_data & 0x3FF  # 10 bits
            humidity_raw = (bit_data >> 10) & 0xFF  # 8 bits
            illumination_raw = (bit_data >> 18) & 0x1FFFF  # 17 bits
            accel_x_raw = (bit_data >> 35) & 0x3FF  # 10 bits
            accel_y_raw = (bit_data >> 45) & 0x3FF  # 10 bits
            accel_z_raw = (bit_data >> 55) & 0x3FF  # 10 bits
            accel_status = (bit_data >> 65) & 0x03  # 2 bits
            magnet_contact = (bit_data >> 67) & 0x01  # 1 bit

            # Apply scaling according to D2-14-41 specification
            temperature_c = -40.0 + (temp_raw * 100.0 / 1023.0)  # -40°C to +60°C
            humidity_percent = humidity_raw * 100.0 / 255.0  # 0% to 100%
            illumination_lx = illumination_raw * 100000.0 / 131071.0  # 0 to 100000 lx

            # Acceleration: ±2.5g range
            accel_x_g = ((accel_x_raw - 512) * 5.0) / 1023.0
            accel_y_g = ((accel_y_raw - 512) * 5.0) / 1023.0
            accel_z_g = ((accel_z_raw - 512) * 5.0) / 1023.0

            # Validate ranges to confirm this is D2-14-41
            if not (-50 <= temperature_c <= 70):
                return None
            if not (0 <= humidity_percent <= 105):
                return None

            return {
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

        except Exception as e:
            self.logger.debug(f"D2-14-41 decode error: {e}")
            return None

    def _decode_d2_14_40(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode D2-14-40: Multi-sensor without magnet contact"""
        if not payload.startswith(b'\x14\x40'):
            return None
        result = self._decode_d2_14_41(payload)
        if result:
            result['eep_profile'] = 'D2-14-40'
            # Remove magnet contact for this profile
            if 'magnet_contact' in result:
                del result['magnet_contact']
            if 'debug_raw_values' in result and 'magnet_raw' in result['debug_raw_values']:
                del result['debug_raw_values']['magnet_raw']
        return result

    def _decode_d2_01_12(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode D2-01-12: Temperature and humidity sensor"""
        if len(payload) < 4:
            return None
        if not payload.startswith(b'\x01\x12'):
            return None

        try:
            arrangements = [
                # (temp_bytes, humidity_byte, temp_offset, temp_scale, hum_scale)
                ((0, 1), 2, -40, 100 / 1023, 100 / 255),  # Standard
                ((1, 2), 3, -273.15, 0.1, 1),  # Alternative
                ((0, 1), 2, 0, 0.01, 0.4),  # Simple
                ((1, 0), 2, -2000, 0.01, 1),  # Reversed bytes
            ]

            for (temp_byte1, temp_byte2), hum_byte, temp_offset, temp_scale, hum_scale in arrangements:
                if len(payload) <= max(temp_byte1, temp_byte2, hum_byte):
                    continue

                temp_raw = (payload[temp_byte1] << 8) | payload[temp_byte2]
                humidity_raw = payload[hum_byte] if hum_byte < len(payload) else 0

                temp_c = temp_offset + (temp_raw * temp_scale)
                humidity_percent = humidity_raw * hum_scale

                if -50 <= temp_c <= 70 and 0 <= humidity_percent <= 100:
                    return {
                        'type': 'temp_humidity',
                        'temperature_c': round(temp_c, 2),
                        'temperature_f': round(temp_c * 9 / 5 + 32, 2),
                        'humidity_percent': round(humidity_percent, 1),
                        'eep_profile': 'D2-01-12',
                        'debug_raw_values': {
                            'temp_raw': temp_raw,
                            'humidity_raw': humidity_raw,
                            'arrangement': f"temp:{temp_byte1}-{temp_byte2}, hum:{hum_byte}"
                        }
                    }
        except Exception:
            pass

        return None

    def _decode_d2_01_01(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode D2-01-01: Electronic switch with energy measurement"""
        if len(payload) < 4:
            return None

        try:
            cmd = payload[0]
            io_channel = payload[1] if len(payload) > 1 else 0
            output_value = payload[2] if len(payload) > 2 else 0

            # Try to extract power/energy if available
            power = 0
            energy = 0
            if len(payload) >= 6:
                power = payload[3] | (payload[4] << 8)
            if len(payload) >= 8:
                energy = payload[5] | (payload[6] << 8) | (payload[7] << 16)

            return {
                'type': 'electronic_switch',
                'command': cmd,
                'io_channel': io_channel,
                'output_value': output_value,
                'power_w': power,
                'energy_wh': energy,
                'eep_profile': 'D2-01-01'
            }
        except Exception:
            return None

    def _decode_d2_05_00(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode D2-05-00: Blind control"""
        if len(payload) < 3:
            return None

        try:
            cmd = payload[0]
            position = payload[1] if len(payload) > 1 else 0
            angle = payload[2] if len(payload) > 2 else 0

            return {
                'type': 'blind_control',
                'command': cmd,
                'position_percent': position,
                'angle_percent': angle,
                'eep_profile': 'D2-05-00'
            }
        except Exception:
            return None

    def _try_pattern_matching(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Try various common VLD patterns"""
        patterns = [
            self._pattern_simple_temp_humidity,
            self._pattern_occupancy_sensor,
            self._pattern_contact_sensor,
            self._pattern_energy_meter,
        ]

        for pattern in patterns:
            try:
                result = pattern(payload)
                if result:
                    return result
            except Exception as e:
                self.logger.debug(f"Pattern {pattern.__name__} failed: {e}")
                continue

        return None

    def _pattern_simple_temp_humidity(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Simple temperature/humidity pattern"""
        if len(payload) < 4:
            return None

        # Try different arrangements
        for i in range(min(len(payload) - 1, 3)):
            temp_raw = (payload[i] << 8) | payload[i + 1]
            humidity = payload[i + 2] if i + 2 < len(payload) else 0

            # Try different scaling
            for temp_offset, temp_scale in [(-1000, 10), (-2000, 10), (0, 100)]:
                temp_c = (temp_raw + temp_offset) / temp_scale

                if -40 <= temp_c <= 80 and 0 <= humidity <= 100:
                    return {
                        'type': 'temp_humidity',
                        'temperature_c': round(temp_c, 1),
                        'temperature_f': round(temp_c * 9 / 5 + 32, 1),
                        'humidity_percent': humidity,
                        'pattern': f'simple_th_offset_{temp_offset}_scale_{temp_scale}'
                    }
        return None

    def _pattern_occupancy_sensor(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Occupancy sensor pattern"""
        if len(payload) < 2:
            return None

        # Look for binary occupancy patterns
        occupancy_byte = payload[0]
        if occupancy_byte in [0x00, 0x01, 0xFF]:
            return {
                'type': 'occupancy',
                'occupied': occupancy_byte != 0x00,
                'pattern': 'simple_occupancy'
            }
        return None

    def _pattern_contact_sensor(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Contact sensor pattern"""
        if len(payload) < 1:
            return None

        contact_byte = payload[0]
        if contact_byte in [0x00, 0x01, 0x09, 0x08]:
            return {
                'type': 'contact',
                'state': 'open' if contact_byte in [0x00, 0x08] else 'closed',
                'pattern': 'simple_contact'
            }
        return None

    def _pattern_energy_meter(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Energy meter pattern"""
        if len(payload) < 4:
            return None

        try:
            energy = payload[0] | (payload[1] << 8) | (payload[2] << 16) | (payload[3] << 24)
            if 0 <= energy <= 1000000:  # Reasonable energy range
                return {
                    'type': 'energy_meter',
                    'energy_wh': energy,
                    'pattern': 'simple_energy'
                }
        except Exception:
            pass
        return None

    def _analyze_vld_payload(self, payload: bytes) -> Dict[str, Any]:
        """Comprehensive VLD payload analysis"""
        analysis = {
            'possible_temps': [],
            'possible_humidity': [],
            'bit_patterns': [],
            'byte_analysis': []
        }

        # Analyze each byte
        for i, byte in enumerate(payload[:16]):  # Limit to first 16 bytes
            analysis['byte_analysis'].append({
                'position': i,
                'value': byte,
                'hex': f"0x{byte:02X}",
                'binary': f"{byte:08b}",
                'possible_meaning': self._guess_byte_meaning(byte, i)
            })

        # Look for temperature patterns
        if len(payload) >= 4:
            for i in range(len(payload) - 1):
                val16_be = (payload[i] << 8) | payload[i + 1]
                val16_le = payload[i] | (payload[i + 1] << 8)

                for val, endian in [(val16_be, 'BE'), (val16_le, 'LE')]:
                    # Try different temperature scalings
                    for offset, scale in [(-2000, 10), (-1000, 10), (0, 100), (-40 * 10, 10)]:
                        temp_c = (val + offset) / scale
                        if -50 <= temp_c <= 100:
                            analysis['possible_temps'].append({
                                'bytes': f"{i}-{i + 1}({endian})",
                                'temp_c': round(temp_c, 1),
                                'raw': val,
                                'formula': f"({val}+{offset})/{scale}"
                            })

                # Check for humidity (0-100 range)
                if 0 <= payload[i] <= 100:
                    analysis['possible_humidity'].append({
                        'byte': i,
                        'value': payload[i]
                    })

        # Look for multi-sensor bit patterns
        if len(payload) >= 9:
            analysis['bit_patterns'].append({
                'type': 'D2-14-41_candidate',
                'length': 9,
                'confidence': self._calculate_d2_14_41_confidence(payload[:9])
            })

        return analysis

    def _guess_byte_meaning(self, byte: int, position: int) -> str:
        """Guess what a byte might represent"""
        if 0 <= byte <= 100:
            return "humidity/percentage"
        elif byte == 0x00 or byte == 0xFF:
            return "binary_state/flag"
        elif 200 <= byte <= 255:
            return "high_value/status"
        elif position == 0:
            return "command/header"
        else:
            return "data/unknown"

    def _calculate_d2_14_41_confidence(self, payload: bytes) -> float:
        """Calculate confidence that this is D2-14-41 data"""
        if len(payload) != 9:
            return 0.0

        confidence = 0.0

        # Check if bit extraction gives reasonable values
        try:
            bit_data = 0
            for i, byte in enumerate(payload):
                bit_data |= (byte << (8 * i))

            temp_raw = bit_data & 0x3FF
            humidity_raw = (bit_data >> 10) & 0xFF

            temp_c = -40.0 + (temp_raw * 100.0 / 1023.0)
            humidity_percent = humidity_raw * 100.0 / 255.0

            if -50 <= temp_c <= 70:
                confidence += 0.4
            if 0 <= humidity_percent <= 100:
                confidence += 0.4
            if temp_c > 0 and humidity_percent > 10:  # Reasonable indoor values
                confidence += 0.2

        except Exception:
            pass

        return confidence

    def _guess_eep_profile(self, payload: bytes) -> List[Dict[str, Any]]:
        """Guess possible EEP profiles based on payload analysis"""
        candidates = []

        length = len(payload)

        # D2-14-41: 9-byte multi-sensor
        if length == 9:
            confidence = self._calculate_d2_14_41_confidence(payload)
            candidates.append({
                'eep': 'D2-14-41',
                'description': 'Multi-sensor (temp/humidity/accel/magnet)',
                'confidence': confidence,
                'reason': f'9-byte payload, confidence {confidence:.1f}'
            })

        # D2-01-12: Simple temp/humidity
        if 4 <= length <= 8:
            candidates.append({
                'eep': 'D2-01-12',
                'description': 'Temperature and humidity sensor',
                'confidence': 0.6,
                'reason': f'{length}-byte payload suitable for temp/humidity'
            })

        # D2-01-01: Electronic switch
        if 3 <= length <= 10:
            candidates.append({
                'eep': 'D2-01-01',
                'description': 'Electronic switch with energy measurement',
                'confidence': 0.4,
                'reason': f'{length}-byte payload suitable for switch control'
            })

        return sorted(candidates, key=lambda x: x['confidence'], reverse=True)
