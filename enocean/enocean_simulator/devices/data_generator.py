# # File: devices/data_generator.py
import random

from protocol.enums import EEPType
from protocol.esp3 import ESP3Protocol


class DataGenerator:
    """Base class for all data generators."""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        raise NotImplementedError("Subclasses must implement this method.")

    @staticmethod
    def update_telegram_checksums(telegram: bytearray) -> bytearray:
        return ESP3Protocol.update_telegram_checksums(telegram)


# --- ENVIRONMENTAL SENSORS (A5 RORG) ---

class TemperatureGenerator(DataGenerator):
    """A5-02-01: Temperature Sensor (-40°C to +40°C)"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)
        temp = random.uniform(18.0, 26.0)

        db3_temp = int(((40.0 - temp) * 255.0 / 80.0)) & 0xFF
        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = db3_temp  # DB3
        new_telegram[8] = 0x00  # FIX: Explicitly set DB2 to 0
        new_telegram[9] = 0x00  # FIX: Explicitly set DB1 to 0
        new_telegram[10] = random.randint(0, 255) | 0x08
        return DataGenerator.update_telegram_checksums(new_telegram)


class TemperatureRangeGenerator(DataGenerator):
    """A5-02-02: Temperature Range Sensor (0°C to +40°C)"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        temp = random.uniform(15.0, 30.0)

        # A5-02-02: temp_c = (255 - DB3) * 40 / 255
        # Inverse: DB3 = 255 - (temp * 255 / 40)
        # db3_temp = int(255 - (temp * 255 / 40)) & 0xFF
        db3_temp = int(((40.0 - temp) * 255.0 / 40.0)) & 0xFF
        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = db3_temp  # DB3
        # new_telegram[10] = random.randint(0, 255) & ~0x08  # DB0 learn bit cleared
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit to 1 for data

        return DataGenerator.update_telegram_checksums(new_telegram)


# enocean-simulator/devices/data_generator.py

class HumidityGenerator(DataGenerator):
    """A5-10-01: Humidity Sensor"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)
        humidity = random.uniform(40.0, 60.0)

        # CORRECT EEP FORMULA: Scale 0-100% to 0-250. Uses DB2.
        db2_humidity = int((humidity * 250.0 / 100.0)) & 0xFF

        # A pure A5-10-01 packet must have its other data bytes set to 0.
        new_telegram[6] = 0xA5
        new_telegram[7] = 0x00  # Explicitly set DB3 to 0
        new_telegram[8] = db2_humidity  # Set the humidity value in DB2
        new_telegram[9] = 0x00  # Explicitly set DB1 to 0
        new_telegram[10] = random.randint(0, 255) | 0x08  # Set learn bit for data

        return DataGenerator.update_telegram_checksums(new_telegram)


class TempHumidityGenerator(DataGenerator):
    """A5-04-01: Temperature + Humidity Sensor"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)
        temp = random.uniform(18.0, 26.0)
        humidity = random.uniform(40.0, 60.0)

        db1_temp = int(((temp + 20.0) * 250.0 / 60.0)) & 0xFF
        db2_humidity = int((humidity * 250.0 / 100.0)) & 0xFF

        new_telegram[6] = 0xA5  # RORG
        new_telegram[7] = 0x00  # DB3 not used in this profile
        new_telegram[8] = db2_humidity
        new_telegram[9] = db1_temp
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit
        return DataGenerator.update_telegram_checksums(new_telegram)


class TempIlluminanceGenerator(DataGenerator):
    """A5-06-01: Temperature + Illuminance"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)
        temp = random.uniform(18.0, 26.0)
        lux = random.uniform(200, 1000)

        # CORRECTED EEP FORMULAS FOR A5-06-01:
        db2_temp = int(((50.0 - temp) * 255.0 / 50.0)) & 0xFF  # Scale 0-50C
        db3_lux = int(lux * 255.0 / 1000.0) & 0xFF  # Scale 0-1000lx

        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = db3_lux
        new_telegram[8] = db2_temp
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = random.randint(0, 255) | 0x08
        return DataGenerator.update_telegram_checksums(new_telegram)


class TempHumidityIlluminanceGenerator(DataGenerator):
    """A5-06-02: Temperature + Humidity + Illuminance"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        temp = random.uniform(18.0, 26.0)
        humidity = random.uniform(40.0, 60.0)
        lux = random.uniform(200, 1000)

        # A5-06-02 formulas
        db1_humidity = int(humidity * 255 / 100) & 0xFF
        db2_temp = int(255 - ((temp + 40) * 255 / 80)) & 0xFF
        db3_lux = int(lux * 255 / 1000) & 0xFF

        new_telegram[6] = 0xA5
        new_telegram[7] = db3_lux  # DB3
        new_telegram[8] = db2_temp  # DB2
        new_telegram[9] = db1_humidity  # DB1
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit to 1 for data

        return DataGenerator.update_telegram_checksums(new_telegram)


class BarometricGenerator(DataGenerator):
    """A5-10-10: Barometric Pressure"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        pressure = random.uniform(980.0, 1030.0)

        # A5-10-10: pressure = 500 + (DB2 * 615 / 255)
        # Inverse: DB2 = (pressure - 500) * 255 / 615
        db2_pressure = int((pressure - 500) * 255 / 615) & 0xFF

        new_telegram[6] = 0xA5
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = db2_pressure  # DB2
        new_telegram[9] = 0x00  # #unused
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit to 1 for data

        return DataGenerator.update_telegram_checksums(new_telegram)


class TempHumidityBarometricGenerator(DataGenerator):
    """A5-10-11: Temperature + Humidity + Barometric"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        temp = random.uniform(18.0, 26.0)
        humidity = random.uniform(40.0, 60.0)
        pressure = random.uniform(980.0, 1030.0)

        # A5-10-11 formulas
        db1_temp = int(255 - ((temp + 40) * 255 / 80)) & 0xFF
        db2_humidity = int(humidity * 255 / 100) & 0xFF
        db3_pressure = int((pressure - 500) * 255 / 615) & 0xFF

        new_telegram[6] = 0xA5
        new_telegram[7] = db3_pressure  # DB3
        new_telegram[8] = db2_humidity  # DB2
        new_telegram[9] = db1_temp  # DB1
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit to 1 for data

        return DataGenerator.update_telegram_checksums(new_telegram)


# --- AIR QUALITY SENSORS (A5 RORG) ---

class CO2Generator(DataGenerator):
    """A5-09-04: CO2 Sensor"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Realistic CO2 levels with occasional spikes
        co2 = random.randint(400, 1200)
        if random.random() < 0.1:  # 10% chance of high CO2
            co2 = random.randint(1200, 2000)

        # A5-09-04: co2 = DB2 * 2000 / 255
        db2_co2 = int(co2 * 255.0 / 2500.0) & 0xFF

        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = db2_co2  # DB2
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = random.randint(0, 255) | 0x08  # Set learn bit

        return DataGenerator.update_telegram_checksums(new_telegram)


class AirQualityGenerator(DataGenerator):
    """A5-09-05: Air Quality Index"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # AQI ranges: 0-50 good, 51-100 moderate, 101+ unhealthy
        aqi = random.choices([
            random.randint(10, 50),  # Good air quality
            random.randint(51, 100),  # Moderate
            random.randint(101, 200)  # Unhealthy
        ], weights=[0.7, 0.25, 0.05])[0]

        db2_aqi = int(aqi * 255 / 300) & 0xFF

        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = db2_aqi  # DB2
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit

        return DataGenerator.update_telegram_checksums(new_telegram)


class VOCGenerator(DataGenerator):
    """A5-09-06: VOC (Volatile Organic Compounds) Sensor"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # VOC levels in ppb (parts per billion)
        voc = random.randint(0, 200)

        db2_voc = int(voc * 255 / 500) & 0xFF

        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = db2_voc  # DB2
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit

        return DataGenerator.update_telegram_checksums(new_telegram)


# --- LIGHT AND OCCUPANCY SENSORS (A5 RORG) ---

class LightSensorGenerator(DataGenerator):
    """A5-06-01: Light Sensor"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)
        lux = random.randint(200, 1000)  # a more realistic data can be generated

        db3_lux = int(lux * 255 / 1000) & 0xFF

        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = db3_lux  # DB3
        new_telegram[8] = 0x00  # Unused
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit

        return DataGenerator.update_telegram_checksums(new_telegram)


class MotionSensorGenerator(DataGenerator):
    """A5-07-01: Motion Sensor"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Motion detection with realistic probability
        motion = random.choices([True, False], weights=[0.15, 0.85])[0]

        # A5-07-01: DB0 bit 3 indicates motion (0 = motion, 1 = no motion)
        motion_bit = 0x00 if motion else 0x08

        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = 0x00  # Unused
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = motion_bit  # DB0

        return DataGenerator.update_telegram_checksums(new_telegram)


class MotionTempSensorGenerator(DataGenerator):
    """A5-07-02: Motion + Temperature Sensor"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        temp = random.uniform(18.0, 26.0)
        motion = random.choices([True, False], weights=[0.15, 0.85])[0]

        db2_temp = int(255 - ((temp + 40) * 255 / 80)) & 0xFF
        motion_bit = 0x00 if motion else 0x08
        new_telegram[6] = 0xA5  # EXPLICIT RORG
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = db2_temp  # DB2
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = motion_bit  # DB0

        return DataGenerator.update_telegram_checksums(new_telegram)


# --- CONTACT AND SECURITY SENSORS (D5 RORG) ---

class ContactGenerator(DataGenerator):
    """D5-00-01: Contact Sensor (Door/Window)"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # D5 uses single data byte: 0x09 = closed, 0x08 = open
        contact_state = random.choices([0x09, 0x08], weights=[0.8, 0.2])[0]  # Mostly closed

        new_telegram[6] = 0xD5  # RORG
        new_telegram[7] = contact_state  # D5 data byte

        return DataGenerator.update_telegram_checksums(new_telegram)


class WindowHandleGenerator(DataGenerator):
    """D5-00-02: Window Handle"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Window handle positions: 0x00=closed, 0x40=tilted, 0x80=open, 0xC0=intermediate
        positions = [0x00, 0x40, 0x80, 0xC0]
        weights = [0.7, 0.15, 0.10, 0.05]  # Mostly closed
        position = random.choices(positions, weights=weights)[0]

        new_telegram[6] = 0xD5  # RORG
        new_telegram[7] = position  # D5 data byte

        return DataGenerator.update_telegram_checksums(new_telegram)


class DoorHandleGenerator(DataGenerator):
    """D5-00-03: Door Handle"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Door handle positions: 0x00=closed, 0x40=down, 0x80=up
        positions = [0x00, 0x40, 0x80]
        weights = [0.8, 0.1, 0.1]  # Mostly closed
        position = random.choices(positions, weights=weights)[0]

        new_telegram[6] = 0xD5  # RORG
        new_telegram[7] = position  # D5 data byte

        return DataGenerator.update_telegram_checksums(new_telegram)


# --- SWITCHES AND CONTROLS (F6 RORG) ---

class RockerSwitchGenerator(DataGenerator):
    """F6-02-01/02: Rocker Switch"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # F6 rocker switch states matching gateway's _decode_button_combination
        actions = [0x00, 0x10, 0x30, 0x50, 0x70]  # All released, D, A, C, B pressed
        weights = [0.7, 0.075, 0.075, 0.075, 0.075]  # Mostly released
        action = random.choices(actions, weights=weights)[0]

        new_telegram[6] = 0xF6  # RORG
        new_telegram[7] = action  # F6 data byte

        return DataGenerator.update_telegram_checksums(new_telegram)


class PushButtonGenerator(DataGenerator):
    """F6-02-03: Push Button"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Simple push button: 0x00 = released, 0x10 = pressed
        pressed = random.choices([0x00, 0x10], weights=[0.8, 0.2])[0]

        new_telegram[6] = 0xF6  # RORG
        new_telegram[7] = pressed  # F6 data byte

        return DataGenerator.update_telegram_checksums(new_telegram)


class MechanicalHandleGenerator(DataGenerator):
    """F6-10-00: Mechanical Handle"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Mechanical handle positions
        positions = [0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xE0]
        position = random.choice(positions)

        new_telegram[6] = 0xF6  # RORG
        new_telegram[7] = position  # F6 data byte

        return DataGenerator.update_telegram_checksums(new_telegram)


# --- VLD DEVICES (D2 RORG) ---


# class VLDTempHumidityGenerator(DataGenerator):
#     """D2-14-41: VLD Multi-sensor with Temperature and Humidity (CORRECTED)"""
#
#     @staticmethod
#     def generate(eep_type: EEPType, base_telegram: bytes) -> bytes:
#         # --- Step 1: Extract the original Sender ID from the base telegram ---
#         # The base_telegram is a full ESP3 packet: 55...[sender_id]...[crc]
#         # The sender_id is the 4 bytes located 6 bytes from the end of the packet,
#         # just before the status byte and the two checksums.
#         # Example: ... [S1][S2][S3][S4] [Status] [CRC8H] [CRC8D]
#         # UPDATE: Looking at ESP3Protocol.create_telegram, it's actually:
#         # ... [S1][S2][S3][S4] [Status] [CRC8D]
#         # So it's 6 bytes from the end of the data payload, or 2 bytes from the packet end.
#         # Let's use the ESP3 protocol structure for robustness.
#         # [Sync(1)] [Header(4)] [CRC8H(1)] [Data(N)] [CRC8D(1)]
#         # Data = [RORG(1)] + [Payload(X)] + [SenderID(4)] + [Status(1)]
#         # The sender ID is at the end of the data block, just before the status.
#         # A simple, robust way is to grab it relative to the end of the packet.
#         # The packet ends with [Status][CRC8D]. Sender ID is the 4 bytes before that.
#         original_sender_id = base_telegram[-7:-3]
#
#         # --- Step 2: Generate new sensor data (same as before) ---
#         temperature_c = random.uniform(18.0, 26.0)
#         humidity_percent = random.uniform(40.0, 60.0)
#         # ... (rest of your sensor value generation) ...
#         temp_raw = int(((temperature_c - (-40.0)) * 1023.0 / 100.0)) & 0x3FF
#         humidity_raw = int(humidity_percent * 255.0 / 100.0) & 0xFF
#         illumination_raw = int(random.uniform(50, 500) * 131071.0 / 100000.0) & 0x1FFFF
#         accel_x_raw = int((random.uniform(-0.1, 0.1) * 1023.0 / 5.0) + 512) & 0x3FF
#         accel_y_raw = int((random.uniform(-0.1, 0.1) * 1023.0 / 5.0) + 512) & 0x3FF
#         accel_z_raw = int((random.uniform(0.95, 1.05) * 1023.0 / 5.0) + 512) & 0x3FF
#         accel_status = random.randint(0, 3)
#         magnet_contact = random.choice([0, 1])
#
#         # --- Step 3: Pack the VLD data payload ---
#         header = bytearray([
#             0xD2,  # RORG
#             0x14,  # FUNC
#             0x41,  # TYPE
#             0x00  # Manufacturer ID
#         ])
#         bit_data = (
#                 (temp_raw << 62) | (humidity_raw << 54) | (illumination_raw << 37) |
#                 (accel_x_raw << 27) | (accel_y_raw << 17) | (accel_z_raw << 7) |
#                 (accel_status << 5) | (magnet_contact << 4)
#         )
#         payload = bytearray(9)
#         for i in range(9):
#             payload[i] = (bit_data >> (8 * i)) & 0xFF
#
#         # --- Step 4: Build a new, correct ESP3 packet from scratch ---
#         rorg = header[0]
#         # The 'data' for create_telegram is everything AFTER the RORG
#         vld_data_payload = header[1:] + payload
#
#         # Give it a good signal strength
#         status = 0x80 | 0x0F
#
#         # Use the utility to create a new, correctly sized and checksum packet
#         final_telegram = ESP3Protocol.create_telegram(
#             rorg,
#             vld_data_payload,
#             original_sender_id,
#             status
#         )
#
#         return final_telegram


# Add these to: enocean-simulator/devices/data_generator.py

class VLDMultiSensorGenerator(DataGenerator):
    """
    Generator for D2-14-41: The full multi-sensor with magnet.
    This is the perfect mirror image of the _decode_d2_14_41 function.
    """

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        # --- 1. Generate realistic sensor values ---
        temperature_c = random.uniform(18.0, 26.0)
        humidity_percent = random.uniform(40.0, 60.0)
        illumination_lx = random.uniform(50, 800)
        # Simulate a device at rest on a table
        accel_x_g = random.uniform(-0.05, 0.05)
        accel_y_g = random.uniform(-0.05, 0.05)
        accel_z_g = random.uniform(0.95, 1.05)
        magnet_contact = random.choice([0, 1])  # 0=closed, 1=open
        accel_status = 0  # 0 = OK

        # temp_raw = (temp - min) * 1023 / (max - min)
        temp_raw = int((temperature_c - (-40.0)) * 1023.0 / 100.0) & 0x3FF
        humidity_raw = int(humidity_percent * 255.0 / 100.0) & 0xFF
        illumination_raw = int(illumination_lx * 131071.0 / 100000.0) & 0x1FFFF
        # accel_raw = (accel_g * 1023 / 5.0) + 512
        accel_x_raw = int((accel_x_g * 1023.0 / 5.0) + 512) & 0x3FF
        accel_y_raw = int((accel_y_g * 1023.0 / 5.0) + 512) & 0x3FF
        accel_z_raw = int((accel_z_g * 1023.0 / 5.0) + 512) & 0x3FF

        # --- 3. Pack bits into a single 72-bit integer (big-endian bit layout) ---
        bit_data = (
                (temp_raw << 62) |
                (humidity_raw << 54) |
                (illumination_raw << 37) |
                (accel_x_raw << 27) |
                (accel_y_raw << 17) |
                (accel_z_raw << 7) |
                (accel_status << 5) |
                (magnet_contact << 4)
            # 4 unused bits at the end
        )

        # --- 4. Convert the large integer into a 9-byte array (big-endian) ---
        sensor_payload = bit_data.to_bytes(9, 'big')

        # --- 5. Construct the full VLD data payload ---
        # This is [FUNC, TYPE, MFG_ID] + [9 bytes of sensor data]
        func = 0x14
        type = 0x41
        mfg_id = 0x00
        vld_eep_data = bytes([func, type, mfg_id]) + sensor_payload

        # --- 6. Create the final ESP3 packet ---
        rorg = 0xD2
        status = 0x80 | 0x0F  # Good RSSI
        return ESP3Protocol.create_telegram(rorg, vld_eep_data, sender_id, status)


class VLDMultiSensorNoMagnetGenerator(VLDMultiSensorGenerator):
    """
    Generator for D2-14-40: Same as D2-14-41 but the magnet bit is ignored.
    We can reuse the D2-14-41 generator as the structure is identical.
    """
    pass  # No changes needed, it inherits the working generator.


class VLDTempHumidityGenerator(DataGenerator):
    """
    Generator for D2-01-12: A simpler VLD temp/humidity sensor.
    """

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        temperature_c = random.uniform(18.0, 26.0)
        humidity_percent = random.uniform(40.0, 60.0)

        # Use the standard formulas for this EEP
        # Temp: 10 bits, -40 to 60C. Humidity: 8 bits, 0-100%
        temp_raw = int((temperature_c - (-40.0)) * 1023.0 / 100.0) & 0x3FF
        humidity_raw = int(humidity_percent * 255.0 / 100.0) & 0xFF

        # This EEP often just sends the raw bytes directly
        # Let's pack them into a 4-byte payload for this example
        # Payload: Temp MSB, Temp LSB, Humidity, Unused
        sensor_payload = bytes([
            (temp_raw >> 8) & 0xFF,
            temp_raw & 0xFF,
            humidity_raw,
            0x00  # Unused byte
        ])

        # VLD Header
        func = 0x01
        type = 0x12
        mfg_id = 0x00
        vld_eep_data = bytes([func, type, mfg_id]) + sensor_payload

        rorg = 0xD2
        status = 0x80 | 0x0F
        return ESP3Protocol.create_telegram(rorg, vld_eep_data, sender_id, status)


# --- UTE DEVICES (D4 RORG) ---

class UTEDeviceGenerator(DataGenerator):
    """D4-00-xx: Universal Teach-In"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        new_telegram[6] = 0xD4  # RORG
        # Fill with teach-in data
        new_telegram[7] = random.randint(0, 255)
        new_telegram[8] = random.randint(0, 255)
        new_telegram[9] = random.randint(0, 255)
        new_telegram[10] = random.randint(0, 255)
        new_telegram[11] = 0xA5  # EEP RORG
        new_telegram[12] = 0x07  # EEP FUNC
        new_telegram[13] = 0x02  # EEP TYPE

        return DataGenerator.update_telegram_checksums(new_telegram)


class GenericA5Generator(DataGenerator):
    """Generic A5 generator for devices without specific implementation"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Generate random but valid A5 data
        new_telegram[7] = random.randint(0, 255)  # DB3
        new_telegram[8] = random.randint(0, 255)  # DB2
        new_telegram[9] = random.randint(0, 255)  # DB1
        new_telegram[10] = random.randint(0, 255) | 0x08  # FIX: Set learn bit to 1 for data

        return DataGenerator.update_telegram_checksums(new_telegram)


class GenericD2Generator(DataGenerator):
    """Generic D2 generator for VLD devices without specific implementation"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        new_telegram[6] = 0xD2  # RORG
        new_telegram[7] = random.randint(0, 255)  # Random VLD data

        return DataGenerator.update_telegram_checksums(new_telegram)


# Add these to: enocean-simulator/devices/data_generator.py

class AccelerometerGenerator(DataGenerator):
    """A5-04-02: Accelerometer (X/Y/Z axes in g)"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Simulate a device at rest, with minor noise
        x_g = random.uniform(-0.05, 0.05)
        y_g = random.uniform(-0.05, 0.05)
        z_g = random.uniform(0.95, 1.05)  # Centered around 1g for gravity

        # Mirror image of the decoder's formula: Raw = (Value - Min) * 255 / (Max - Min)
        db3_x = int((x_g - (-2.0)) * 255.0 / 4.0) & 0xFF
        db2_y = int((y_g - (-2.0)) * 255.0 / 4.0) & 0xFF
        db1_z = int((z_g - (-2.0)) * 255.0 / 4.0) & 0xFF

        # DB0 must be 0x00 for the data packet pattern, then set the learn bit
        db0_val = 0x00 | 0x08

        new_telegram[6] = 0xA5
        new_telegram[7] = db3_x
        new_telegram[8] = db2_y
        new_telegram[9] = db1_z
        new_telegram[10] = db0_val
        return DataGenerator.update_telegram_checksums(new_telegram)


class SoilMoistureGenerator(DataGenerator):
    """A5-09-01: Soil Moisture Sensor (0-100%)"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)
        moisture = random.uniform(30.0, 80.0)

        # Mirror image of decoder: Raw = Value * 250 / 100
        db1_moisture = int(moisture * 250.0 / 100.0) & 0xFF

        new_telegram[6] = 0xA5
        new_telegram[7] = 0x00  # Unused, set to 0
        new_telegram[8] = 0x00  # Unused, set to 0
        new_telegram[9] = db1_moisture
        new_telegram[10] = random.randint(0, 255) | 0x08
        return DataGenerator.update_telegram_checksums(new_telegram)


class RainSensorGenerator(DataGenerator):
    """A5-10-09: Rain Sensor"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Simulate light rain or no rain
        is_raining = random.choice([True, False])
        intensity = random.uniform(10.0, 50.0) if is_raining else 0.0

        db2_intensity = int(intensity * 255.0 / 100.0) & 0xFF
        detection_bit = (1 << 4) if is_raining else 0  # Set bit 4 if detected

        # Start with a random byte, set the detection bit, then set the learn bit
        db0_val = (random.randint(0, 255) | detection_bit) | 0x08

        new_telegram[6] = 0xA5
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = db2_intensity
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = db0_val
        return DataGenerator.update_telegram_checksums(new_telegram)


class SmokeDetectorGenerator(DataGenerator):
    """A5-12-01: Smoke Detector"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        # Mostly no alarm, occasional alarm
        alarm_active = random.random() < 0.05  # 5% chance of alarm
        alarm_bit = (1 << 2) if alarm_active else 0  # Set bit 2 if alarm

        db0_val = (random.randint(0, 255) | alarm_bit) | 0x08

        new_telegram[6] = 0xA5
        new_telegram[7] = 0x00
        new_telegram[8] = 0x00
        new_telegram[9] = 0x00
        new_telegram[10] = db0_val
        return DataGenerator.update_telegram_checksums(new_telegram)


class GlassBreakDetectorGenerator(DataGenerator):
    """A5-12-02: Glass Break Detector"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        alarm_active = random.random() < 0.02  # 2% chance of alarm
        alarm_bit = (1 << 2) if alarm_active else 0
        db0_val = (random.randint(0, 255) | alarm_bit) | 0x08

        new_telegram[6] = 0xA5
        new_telegram[7] = 0x00
        new_telegram[8] = 0x00
        new_telegram[9] = 0x00
        new_telegram[10] = db0_val
        return DataGenerator.update_telegram_checksums(new_telegram)


class VibrationDetectorGenerator(DataGenerator):
    """A5-12-03: Vibration Detector"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        alarm_active = random.random() < 0.10  # 10% chance
        intensity = random.uniform(50.0, 90.0) if alarm_active else random.uniform(0, 10)

        db2_intensity = int(intensity * 255.0 / 100.0) & 0xFF
        alarm_bit = (1 << 2) if alarm_active else 0
        db0_val = (random.randint(0, 255) | alarm_bit) | 0x08

        new_telegram[6] = 0xA5
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = db2_intensity
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = db0_val
        return DataGenerator.update_telegram_checksums(new_telegram)


class FloodDetectorGenerator(DataGenerator):
    """A5-13-01: Flood Detector"""

    @staticmethod
    def generate(eep_type: EEPType, base_telegram: bytes, sender_id: bytes) -> bytes:
        new_telegram = bytearray(base_telegram)

        alarm_active = random.random() < 0.01  # 1% chance
        level = random.uniform(80.0, 100.0) if alarm_active else 0.0

        db2_level = int(level * 255.0 / 100.0) & 0xFF
        alarm_bit = (1 << 2) if alarm_active else 0
        db0_val = (random.randint(0, 255) | alarm_bit) | 0x08

        new_telegram[6] = 0xA5
        new_telegram[7] = 0x00  # Unused
        new_telegram[8] = db2_level
        new_telegram[9] = 0x00  # Unused
        new_telegram[10] = db0_val
        return DataGenerator.update_telegram_checksums(new_telegram)


# --- COMPLETE GENERATOR FACTORY - All 82 devices properly mapped ---

class GeneratorFactory:
    """Factory mapping each EEP type to its correct generator based on RORG and specifications"""

    _generators = {
        # Environmental Sensors (A5 RORG)
        EEPType.TEMPERATURE: TemperatureGenerator,
        EEPType.TEMPERATURE_RANGE: TemperatureRangeGenerator,
        EEPType.HUMIDITY: HumidityGenerator,
        EEPType.TEMPERATURE_HUMIDITY: TempHumidityGenerator,
        EEPType.TEMPERATURE_ILLUMINANCE: TempIlluminanceGenerator,
        EEPType.TEMPERATURE_ILLUMINANCE_HUMIDITY: TempHumidityIlluminanceGenerator,
        EEPType.BAROMETRIC: BarometricGenerator,
        EEPType.TEMP_HUMIDITY_BAROMETRIC: TempHumidityBarometricGenerator,
        EEPType.CO2_SENSOR: CO2Generator,
        EEPType.AIR_QUALITY: AirQualityGenerator,
        EEPType.VOC_SENSOR: VOCGenerator,

        # Light and Motion Sensors (A5 RORG)
        EEPType.LIGHT_SENSOR: LightSensorGenerator,
        EEPType.LIGHT_SENSOR_ILLUMINANCE: LightSensorGenerator,
        EEPType.LIGHT_SENSOR_TEMP_ILLUMINANCE: TempIlluminanceGenerator,
        EEPType.LIGHT_SENSOR_OCCUPANCY: LightSensorGenerator,
        EEPType.MOTION_SENSOR: MotionSensorGenerator,
        EEPType.MOTION_TEMP_SENSOR: MotionTempSensorGenerator,
        EEPType.MOTION_TEMP_ILLUMINANCE_SENSOR: MotionTempSensorGenerator,

        # Specialized Sensors (A5 RORG)
        EEPType.ACCELEROMETER: AccelerometerGenerator,
        EEPType.SOIL_MOISTURE: SoilMoistureGenerator,
        EEPType.RAIN_SENSOR: RainSensorGenerator,
        EEPType.SMOKE_DETECTOR: SmokeDetectorGenerator,
        EEPType.GLASS_BREAK_DETECTOR: GlassBreakDetectorGenerator,
        EEPType.VIBRATION_DETECTOR: VibrationDetectorGenerator,
        EEPType.FLOOD_DETECTOR: FloodDetectorGenerator,

        # HVAC and Climate Control (A5 RORG)
        EEPType.RADIATOR_THERMOSTAT: TempHumidityGenerator,
        EEPType.RADIATOR_THERMOSTAT_WITH_FEEDBACK: TempHumidityGenerator,
        EEPType.FAN_COIL_THERMOSTAT: TempHumidityGenerator,
        EEPType.FLOOR_HEATING_THERMOSTAT: TemperatureGenerator,
        EEPType.HVAC_CONTROL: TempHumidityBarometricGenerator,
        EEPType.SINGLE_ACTUATOR: GenericA5Generator,

        # Energy and Metering (A5 RORG)
        EEPType.MULTI_SENSOR: TempHumidityGenerator,
        EEPType.SOLAR_CELL: GenericA5Generator,
        EEPType.ENERGY_METER: GenericA5Generator,
        EEPType.GAS_METER: GenericA5Generator,
        EEPType.WATER_METER: GenericA5Generator,
        EEPType.ELECTRICITY_METER: GenericA5Generator,

        # Contact and Security Sensors (D5 RORG)
        EEPType.CONTACT: ContactGenerator,
        EEPType.WINDOW_HANDLE: WindowHandleGenerator,
        EEPType.DOOR_HANDLE: DoorHandleGenerator,

        # Switches and Controls (F6 RORG)
        EEPType.ROCKER_SWITCH: RockerSwitchGenerator,
        EEPType.ROCKER_SWITCH_2: RockerSwitchGenerator,
        EEPType.PUSHBUTTON: PushButtonGenerator,
        EEPType.PUSHBUTTON_LATCHING: PushButtonGenerator,
        EEPType.DUAL_PUSHBUTTON: PushButtonGenerator,
        EEPType.ENERGY_HARVESTING_SWITCH: RockerSwitchGenerator,
        EEPType.MECHANICAL_HANDLE: MechanicalHandleGenerator,

        # VLD Devices (D2 RORG)
        EEPType.DIMMER: GenericD2Generator,
        EEPType.DIMMER_2: GenericD2Generator,
        EEPType.LED_CONTROLLER: GenericD2Generator,
        EEPType.RGB_CONTROLLER: GenericD2Generator,
        EEPType.RGBW_CONTROLLER: GenericD2Generator,
        EEPType.ANALOG_INPUT: GenericD2Generator,
        EEPType.ANALOG_OUTPUT: GenericD2Generator,
        EEPType.TEMPERATURE_SETPOINT: GenericD2Generator,
        EEPType.RELATIVE_HUMIDITY_SETPOINT: GenericD2Generator,
        EEPType.AIR_FLOW_SETPOINT: GenericD2Generator,
        EEPType.IO_MODULE: GenericD2Generator,
        EEPType.VALVE_CONTROL: GenericD2Generator,
        EEPType.PUMP_CONTROL: GenericD2Generator,
        EEPType.VEHICLE_SENSOR: GenericD2Generator,
        EEPType.TIRE_PRESSURE: GenericD2Generator,

        EEPType.VLD_OCCUPANCY_ADVANCED: GenericD2Generator,
        EEPType.VLD_WINDOW_ADVANCED: GenericD2Generator,

        EEPType.VLD_MULTI_TEMP_HUMIDITY_ACCEL_MAGNET: VLDMultiSensorGenerator,
        EEPType.VLD_MULTI_TEMP_HUMIDITY_ACCEL: VLDMultiSensorNoMagnetGenerator,
        EEPType.VLD_TEMP_HUMIDITY: VLDTempHumidityGenerator,

        EEPType.VLD_OCCUPANCY_SIMPLE: GenericD2Generator,
        EEPType.VLD_DESK_OCCUPANCY: GenericD2Generator,
        EEPType.VLD_PEOPLE_COUNTER: GenericD2Generator,

        # UTE Devices (D4 RORG)
        EEPType.UTE_SENSOR: UTEDeviceGenerator,
        EEPType.UTE_ACTUATOR: UTEDeviceGenerator,
        EEPType.UTE_SWITCH: UTEDeviceGenerator,

    }

    @classmethod
    def get_generator(cls, eep_type: EEPType) -> DataGenerator:
        """
        Returns the correct generator for the given EEP type.
        Falls back to GenericA5Generator for unknown types.
        """
        generator_class = cls._generators.get(eep_type)
        if generator_class is None:
            print(f"Warning: No specific generator found for {eep_type}, using GenericA5Generator")
            return GenericA5Generator
        return generator_class
