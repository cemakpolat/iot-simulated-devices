# File: protocol/decoder.py - REVISED AND CORRECTED VERSION
from protocol.enums import EEPType

class EEPDecoder:
    """
    Decodes raw EnOcean telegram data based on its EEPType.
    This class contains only static methods for decoding.
    """
    @staticmethod
    def decode(eep: EEPType, data: bytes) -> dict:
        try:
            if not data:
                return {"error": "Payload is empty"}
            decoder_func = DECODER_MAP.get(eep, EEPDecoder._decode_generic)
            return decoder_func(data)
        except IndexError as e:
            return {"error": f"Payload too short for EEP {eep.value}: {e}", "data": data.hex()}
        except Exception as e:
            return {"error": f"An unexpected error occurred during decoding: {e}", "data": data.hex(), "eep": eep.value}

    # --- All static decoder methods (_decode_a5_02_01, etc.) remain the same as the previous correct version ---
    # (The full list of 82 decoders from the previous answer goes here. I'm omitting them for brevity,
    # but they are essential and should be copied from the previous response if you don't have them)
    @staticmethod
    def _decode_generic(data: bytes) -> dict:
        return {"status": "decoded_with_generic_fallback", "rorg": f"0x{data[0]:02X}", "raw_data": data.hex()}
    @staticmethod
    def _decode_a5_02_01(data: bytes) -> dict: return {"temperature": round(-40 + (data[2] * 80 / 255), 1)}
    @staticmethod
    def _decode_a5_02_02(data: bytes) -> dict: return {"temperature": round(data[1] * 40 / 255, 1)}
    @staticmethod
    def _decode_a5_04_01(data: bytes) -> dict: return {"humidity": round(data[1] * 100 / 255, 1), "temperature": round(data[2] * 40 / 255, 1)}
    @staticmethod
    def _decode_a5_02_04(data: bytes) -> dict: return {"illuminance_lux": round(data[1] * 1000 / 255), "temperature": round(-40 + (data[2] * 80 / 255), 1)}
    @staticmethod
    def _decode_a5_02_05(data: bytes) -> dict: return {"illuminance_lux": round(data[1] * 1000 / 255), "temperature": round(-40 + (data[2] * 80 / 255), 1), "humidity": round(data[3] * 100 / 255, 1)}
    @staticmethod
    def _decode_a5_06_01(data: bytes) -> dict: return {"light_lux": round(data[2] * 1000 / 255)}
    @staticmethod
    def _decode_a5_06_02(data: bytes) -> dict: return {"illuminance_lux": round(data[2] * 2000 / 255)}
    @staticmethod
    def _decode_a5_06_03(data: bytes) -> dict: return {"illuminance_lux": round(data[1] * 1000 / 255), "temperature": round(-40 + (data[2] * 80 / 255), 1)}
    @staticmethod
    def _decode_a5_06_04(data: bytes) -> dict: return {"illuminance_lux": round(data[2] * 1000 / 255), "occupied": (data[4] & 0x08) != 0}
    @staticmethod
    def _decode_a5_07_01(data: bytes) -> dict: return {"motion_detected": (data[4] & 0x01) == 0}
    @staticmethod
    def _decode_a5_07_02(data: bytes) -> dict: return {"temperature": round(-40 + (data[2] * 80 / 255), 1), "motion_detected": (data[4] & 0x01) == 0}
    @staticmethod
    def _decode_a5_07_03(data: bytes) -> dict: return {"illuminance_lux": round(data[1] * 1000 / 255), "temperature": round(-40 + (data[2] * 80 / 255), 1), "motion_detected": (data[4] & 0x01) == 0}
    @staticmethod
    def _decode_a5_07_04(data: bytes) -> dict: return {"smoke_alarm": (data[4] & 0x10) != 0}
    @staticmethod
    def _decode_a5_07_05(data: bytes) -> dict: return {"glass_break_alarm": (data[4] & 0x10) != 0}
    @staticmethod
    def _decode_a5_07_06(data: bytes) -> dict: return {"vibration_detected": (data[4] & 0x10) != 0}
    @staticmethod
    def _decode_a5_07_07(data: bytes) -> dict: return {"flood_detected": (data[4] & 0x10) != 0}
    @staticmethod
    def _decode_a5_08_01(data: bytes) -> dict: return {"acceleration_x": round((data[1] * 4 / 255) - 2, 2), "acceleration_y": round((data[2] * 4 / 255) - 2, 2), "acceleration_z": round((data[3] * 4 / 255) - 2, 2)}
    @staticmethod
    def _decode_a5_09_04(data: bytes) -> dict: return {"co2_ppm": round(data[2] * 2000 / 255)}
    @staticmethod
    def _decode_a5_09_05(data: bytes) -> dict: return {"air_quality_index": round(data[2] * 500 / 255)}
    @staticmethod
    def _decode_a5_09_06(data: bytes) -> dict: return {"voc_ppb": round(data[2] * 500 / 255)}
    @staticmethod
    def _decode_a5_10_01(data: bytes) -> dict: return {"humidity": round(data[3] * 100 / 255, 1)}
    @staticmethod
    def _decode_a5_10_02(data: bytes) -> dict: return {"pressure_hpa": round(500 + (data[2] * 615 / 255))}
    @staticmethod
    def _decode_a5_10_03(data: bytes) -> dict: return {"pressure_hpa": round(500 + (data[1] * 615 / 255)), "humidity": round(data[2] * 100 / 255, 1), "temperature": round(data[3] * 40 / 255, 1)}
    @staticmethod
    def _decode_a5_12_01(data: bytes) -> dict: return {"humidity": round(data[1] * 100 / 255, 1), "temperature": round(-40 + (data[2] * 80 / 255), 1), "motion_detected": data[4] == 0x00}
    @staticmethod
    def _decode_a5_12_02(data: bytes) -> dict: return {"solar_power_watts": round(data[2] * 2 / 255, 2)}
    @staticmethod
    def _decode_a5_12_03(data: bytes) -> dict: return {"power_watts": round(data[1] * 1000 / 255)}
    @staticmethod
    def _decode_a5_12_04(data: bytes) -> dict: return {"gas_flow_m3h": round(data[1] * 5 / 255, 2)}
    @staticmethod
    def _decode_a5_12_05(data: bytes) -> dict: return {"water_flow_lpm": round(data[1] * 10 / 255, 1)}
    @staticmethod
    def _decode_a5_12_06(data: bytes) -> dict: return {"electrical_power_watts": round(data[1] * 2000 / 255)}
    @staticmethod
    def _decode_a5_20_01(data: bytes) -> dict: return {"soil_moisture_percent": round(data[2] * 100 / 255)}
    @staticmethod
    def _decode_a5_20_02(data: bytes) -> dict: return {"rain_detected": (data[4] & 0x08) != 0}
    @staticmethod
    def _decode_a5_38_08(data: bytes) -> dict: return {"actuator_position_percent": round(data[2] * 100 / 255)}
    @staticmethod
    def _decode_a5_04_02(data: bytes) -> dict: return {"valve_position_percent": round(data[1] * 100 / 255), "temperature": round(data[2] * 40 / 255, 1), "setpoint": round(data[3] * 40 / 255, 1)}
    @staticmethod
    def _decode_a5_04_03(data: bytes) -> dict: return {"fan_speed": data[1] // 85, "temperature": round(data[2] * 40 / 255, 1)}
    @staticmethod
    def _decode_a5_04_04(data: bytes) -> dict: return {"floor_temperature": round(data[2] * 40 / 255, 1)}
    @staticmethod
    def _decode_a5_10_06(data: bytes) -> dict: return {"fan_speed_percent": round(data[1] * 100 / 255), "humidity": round(data[2] * 100 / 255, 1), "temperature": round(data[3] * 40 / 255, 1)}
    @staticmethod
    def _decode_f6_02_01(data: bytes) -> dict: return {"rocker_action": {0x10: "AI_pressed", 0x30: "AO_pressed", 0x50: "BI_pressed", 0x70: "BO_pressed", 0x00: "released"}.get(data[1] & 0xF0, f"unknown(0x{data[1] & 0xF0:02X})")}
    @staticmethod
    def _decode_f6_02_03(data: bytes) -> dict: return {"button_pressed": (data[1] & 0x10) != 0}
    @staticmethod
    def _decode_f6_02_04(data: bytes) -> dict: return {"button_latched": (data[1] & 0x10) != 0}
    @staticmethod
    def _decode_f6_02_05(data: bytes) -> dict: return {"buttons_pressed": {0x00: "none", 0x10: "button_A", 0x20: "button_B", 0x30: "both"}.get(data[1] & 0x30, "unknown")}
    @staticmethod
    def _decode_f6_02_06(data: bytes) -> dict: return {"switch_action": {0x00: "released", 0x10: "press_A", 0x30: "press_B"}.get(data[1] & 0x30, "unknown")}
    @staticmethod
    def _decode_f6_10_00(data: bytes) -> dict: return {"handle_position": (data[1] & 0xE0) >> 5}
    @staticmethod
    def _decode_d5_00_01(data: bytes) -> dict: return {"contact": "closed" if (data[1] & 0x01) == 0 else "open"}
    @staticmethod
    def _decode_d5_00_02(data: bytes) -> dict: return {"window_handle": {0x0: "closed", 0x4: "tilted", 0x8: "open", 0xC: "locked"}.get((data[1] & 0xF0) >> 4, "unknown")}
    @staticmethod
    def _decode_d5_00_03(data: bytes) -> dict: return {"door_handle": "open" if (data[1] & 0x80) != 0 else "closed"}
    @staticmethod
    def _decode_d2_01_01(data: bytes) -> dict: return {"dim_level": data[1]}
    @staticmethod
    def _decode_d2_01_02(data: bytes) -> dict: return {"dim_level_percent": round(data[1] * 100 / 255), "color_temperature_k": round(2700 + (data[2] * 3800 / 255))}
    @staticmethod
    def _decode_d2_01_03(data: bytes) -> dict: return {"brightness_percent": round(data[1] * 100 / 255)}
    @staticmethod
    def _decode_d2_01_04(data: bytes) -> dict: return {"red": data[1], "green": data[2], "blue": data[3]}
    @staticmethod
    def _decode_d2_01_05(data: bytes) -> dict: return {"red": data[1], "green": data[2], "blue": data[3], "white": data[4]}
    @staticmethod
    def _decode_d2_01_06(data: bytes) -> dict: return {"analog_voltage": round(data[1] * 10 / 255, 2)}
    @staticmethod
    def _decode_d2_01_07(data: bytes) -> dict: return {"output_voltage": round(data[1] * 10 / 255, 2)}
    @staticmethod
    def _decode_d2_01_08(data: bytes) -> dict: return {"temperature_setpoint": round(40 - (data[1] * 40 / 255), 1)}
    @staticmethod
    def _decode_d2_01_09(data: bytes) -> dict: return {"humidity_setpoint_percent": round(data[1] * 100 / 255)}
    @staticmethod
    def _decode_d2_01_10(data: bytes) -> dict: return {"airflow_setpoint_m3h": round(data[1] * 100 / 255)}
    @staticmethod
    def _decode_d2_32_00(data: bytes) -> dict: return {"io_state_binary": f"0b{data[1]:08b}", "io_state_decimal": data[1]}
    @staticmethod
    def _decode_d2_33_00(data: bytes) -> dict: return {"valve_position_percent": data[1]}
    @staticmethod
    def _decode_d2_34_00(data: bytes) -> dict: return {"pump_speed_percent": round(data[1] * 100 / 255)}
    @staticmethod
    def _decode_d2_01_12(data: bytes) -> dict: return {"temperature": round(-40 + (data[1] * 80 / 255), 1), "humidity": round(data[2] * 100 / 255, 1)}
    @staticmethod
    def _decode_d2_06_00(data: bytes) -> dict: return {"occupied": data[1] > 127, "occupancy_level": round(data[1] * 100 / 255)}
    @staticmethod
    def _decode_d2_06_01(data: bytes) -> dict: return {"occupied": data[1] > 127, "confidence_percent": round(data[2] * 100 / 255), "occupancy_level": data[1]}
    @staticmethod
    def _decode_d2_06_02(data: bytes) -> dict: return {"desk_id": data[1], "occupied": data[2] > 127, "occupancy_level": round(data[2] * 100 / 255)}
    @staticmethod
    def _decode_d2_06_03(data: bytes) -> dict: return {"people_entered": data[1], "people_exited": data[2], "net_occupancy": max(0, data[1] - data[2])}
    @staticmethod
    def _decode_d2_06_50(data: bytes) -> dict: return {"position_raw": data[1], "locked": (data[2] & 0x01) != 0, "tamper_detected": (data[2] & 0x02) != 0}
    @staticmethod
    def _decode_d2_14_40(data: bytes) -> dict: return {"temperature": round(-40 + (data[1] * 80 / 255), 1), "humidity": round(data[2] * 100 / 255, 1), "acceleration_x": round((data[3] - 128) * 4 / 255, 2), "acceleration_y": round((data[4] - 128) * 4 / 255, 2), "acceleration_z": round((data[5] - 128) * 4 / 255, 2)}
    @staticmethod
    def _decode_d2_14_41(data: bytes) -> dict: return {"temperature": round(-40 + (data[1] * 80 / 255), 1), "humidity": round(data[2] * 100 / 255, 1), "acceleration_x": round((data[3] - 128) * 4 / 255, 2), "acceleration_y": round((data[4] - 128) * 4 / 255, 2), "acceleration_z": round((data[5] - 128) * 4 / 255, 2), "magnetic_field_ut": round((data[6] - 128) * 100 / 255, 1)}
    @staticmethod
    def _decode_d2_40_00(data: bytes) -> dict: return {"speed_kmh": round(data[1] * 200 / 255), "fuel_level_percent": round(data[2] * 100 / 255)}
    @staticmethod
    def _decode_d2_41_00(data: bytes) -> dict: return {"tire_pressure_bar": round(1.0 + (data[1] * 2.5 / 255), 2), "tire_temperature": round(-40 + (data[2] * 120 / 255), 1)}
    @staticmethod
    def _decode_d4_00_01(data: bytes) -> dict: return {"sensor_type": {1: "temperature", 2: "humidity", 3: "pressure"}.get(data[1], f"type_{data[1]}"), "value": data[2]}
    @staticmethod
    def _decode_d4_00_02(data: bytes) -> dict: return {"actuator_type": {1: "valve", 2: "damper", 3: "motor"}.get(data[1], f"type_{data[1]}"), "position_percent": round(data[2] * 100/255)}
    @staticmethod
    def _decode_d4_00_03(data: bytes) -> dict: return {"channel": data[1], "switch_state": "on" if data[2] == 0x01 else "off"}
    @staticmethod
    def _decode_c5_00_01(data: bytes) -> dict: return {"gateway_status": "online" if data[1] == 0x00 else "offline", "cpu_load_percent": round(data[2] * 100 / 255)}
    @staticmethod
    def _decode_c5_00_02(data: bytes) -> dict: return {"signal_strength_dbm": round(-100 + (data[1] * 80 / 255)), "repeated_count": data[2]}
    @staticmethod
    def _decode_c5_00_03(data: bytes) -> dict: return {"timestamp": (data[1] << 8) | data[2]}
    @staticmethod
    def _decode_c5_00_04(data: bytes) -> dict: return {"command": {1: "read", 2: "write", 3: "status"}.get(data[1], f"unknown({data[1]})"), "parameter": data[2]}
    @staticmethod
    def _decode_a7_00_01(data: bytes) -> dict: return {"ack_requested": data[1] == 0x01, "sequence_number": data[2]}
    @staticmethod
    def _decode_a7_00_02(data: bytes) -> dict: return {"ack_sent": data[1] == 0x01, "error": {0: "none", 1: "timeout", 2: "invalid"}.get(data[2], f"unknown({data[2]})")}
    @staticmethod
    def _decode_30_00_01(data: bytes) -> dict: return {"security_level": {1: "basic", 2: "medium", 3: "high"}.get(data[1], f"unknown({data[1]})"), "nonce": data[2]}
    @staticmethod
    def _decode_30_00_02(data: bytes) -> dict: return {"hop_count": data[1], "security_verified": data[2] == 0x01}

# CRITICAL FIX: The DECODER_MAP must be defined *after* the class,
# so it can correctly reference the static methods.
DECODER_MAP = {
    EEPType.TEMPERATURE: EEPDecoder._decode_a5_02_01, EEPType.TEMPERATURE_RANGE: EEPDecoder._decode_a5_02_02, EEPType.HUMIDITY: EEPDecoder._decode_a5_10_01,
    EEPType.TEMPERATURE_HUMIDITY: EEPDecoder._decode_a5_04_01, EEPType.RADIATOR_THERMOSTAT: EEPDecoder._decode_a5_04_01, EEPType.TEMPERATURE_ILLUMINANCE: EEPDecoder._decode_a5_02_04,
    EEPType.TEMPERATURE_ILLUMINANCE_HUMIDITY: EEPDecoder._decode_a5_02_05, EEPType.BAROMETRIC: EEPDecoder._decode_a5_10_02, EEPType.TEMP_HUMIDITY_BAROMETRIC: EEPDecoder._decode_a5_10_03,
    EEPType.CO2_SENSOR: EEPDecoder._decode_a5_09_04, EEPType.AIR_QUALITY: EEPDecoder._decode_a5_09_05, EEPType.VOC_SENSOR: EEPDecoder._decode_a5_09_06,
    EEPType.LIGHT_SENSOR: EEPDecoder._decode_a5_06_01, EEPType.LIGHT_SENSOR_ILLUMINANCE: EEPDecoder._decode_a5_06_02, EEPType.LIGHT_SENSOR_TEMP_ILLUMINANCE: EEPDecoder._decode_a5_06_03,
    EEPType.LIGHT_SENSOR_OCCUPANCY: EEPDecoder._decode_a5_06_04, EEPType.MOTION_SENSOR: EEPDecoder._decode_a5_07_01, EEPType.MOTION_TEMP_SENSOR: EEPDecoder._decode_a5_07_02,
    EEPType.MOTION_TEMP_ILLUMINANCE_SENSOR: EEPDecoder._decode_a5_07_03, EEPType.ACCELEROMETER: EEPDecoder._decode_a5_08_01, EEPType.SOIL_MOISTURE: EEPDecoder._decode_a5_20_01,
    EEPType.RAIN_SENSOR: EEPDecoder._decode_a5_20_02, EEPType.CONTACT: EEPDecoder._decode_d5_00_01, EEPType.WINDOW_HANDLE: EEPDecoder._decode_d5_00_02,
    EEPType.DOOR_HANDLE: EEPDecoder._decode_d5_00_03, EEPType.MECHANICAL_HANDLE: EEPDecoder._decode_f6_10_00, EEPType.SMOKE_DETECTOR: EEPDecoder._decode_a5_07_04,
    EEPType.GLASS_BREAK_DETECTOR: EEPDecoder._decode_a5_07_05, EEPType.VIBRATION_DETECTOR: EEPDecoder._decode_a5_07_06, EEPType.FLOOD_DETECTOR: EEPDecoder._decode_a5_07_07,
    EEPType.ROCKER_SWITCH: EEPDecoder._decode_f6_02_01, EEPType.ROCKER_SWITCH_2: EEPDecoder._decode_f6_02_01, EEPType.PUSHBUTTON: EEPDecoder._decode_f6_02_03,
    EEPType.PUSHBUTTON_LATCHING: EEPDecoder._decode_f6_02_04, EEPType.DUAL_PUSHBUTTON: EEPDecoder._decode_f6_02_05, EEPType.ENERGY_HARVESTING_SWITCH: EEPDecoder._decode_f6_02_06,
    EEPType.RADIATOR_THERMOSTAT_WITH_FEEDBACK: EEPDecoder._decode_a5_04_02, EEPType.FAN_COIL_THERMOSTAT: EEPDecoder._decode_a5_04_03, EEPType.FLOOR_HEATING_THERMOSTAT: EEPDecoder._decode_a5_04_04,
    EEPType.HVAC_CONTROL: EEPDecoder._decode_a5_10_06, EEPType.SINGLE_ACTUATOR: EEPDecoder._decode_a5_38_08, EEPType.MULTI_SENSOR: EEPDecoder._decode_a5_12_01,
    EEPType.SOLAR_CELL: EEPDecoder._decode_a5_12_02, EEPType.ENERGY_METER: EEPDecoder._decode_a5_12_03, EEPType.GAS_METER: EEPDecoder._decode_a5_12_04,
    EEPType.WATER_METER: EEPDecoder._decode_a5_12_05, EEPType.ELECTRICITY_METER: EEPDecoder._decode_a5_12_06, EEPType.DIMMER: EEPDecoder._decode_d2_01_01,
    EEPType.DIMMER_2: EEPDecoder._decode_d2_01_02, EEPType.LED_CONTROLLER: EEPDecoder._decode_d2_01_03, EEPType.RGB_CONTROLLER: EEPDecoder._decode_d2_01_04,
    EEPType.RGBW_CONTROLLER: EEPDecoder._decode_d2_01_05, EEPType.ANALOG_INPUT: EEPDecoder._decode_d2_01_06, EEPType.ANALOG_OUTPUT: EEPDecoder._decode_d2_01_07,
    EEPType.TEMPERATURE_SETPOINT: EEPDecoder._decode_d2_01_08, EEPType.RELATIVE_HUMIDITY_SETPOINT: EEPDecoder._decode_d2_01_09, EEPType.AIR_FLOW_SETPOINT: EEPDecoder._decode_d2_01_10,
    EEPType.IO_MODULE: EEPDecoder._decode_d2_32_00, EEPType.VALVE_CONTROL: EEPDecoder._decode_d2_33_00, EEPType.PUMP_CONTROL: EEPDecoder._decode_d2_34_00,
    EEPType.VEHICLE_SENSOR: EEPDecoder._decode_d2_40_00, EEPType.TIRE_PRESSURE: EEPDecoder._decode_d2_41_00, EEPType.GATEWAY: EEPDecoder._decode_c5_00_01,
    EEPType.REPEATER: EEPDecoder._decode_c5_00_02, EEPType.TIME_SERVER: EEPDecoder._decode_c5_00_03, EEPType.CONFIGURATION_TOOL: EEPDecoder._decode_c5_00_04,
    EEPType.SMART_ACK_CLIENT: EEPDecoder._decode_a7_00_01, EEPType.SMART_ACK_GATEWAY: EEPDecoder._decode_a7_00_02, EEPType.SECURE_DEVICE: EEPDecoder._decode_30_00_01,
    EEPType.SECURE_RETRANSMITTER: EEPDecoder._decode_30_00_02, EEPType.UTE_SENSOR: EEPDecoder._decode_d4_00_01, EEPType.UTE_ACTUATOR: EEPDecoder._decode_d4_00_02,
    EEPType.UTE_SWITCH: EEPDecoder._decode_d4_00_03, EEPType.VLD_TEMP_HUMIDITY: EEPDecoder._decode_d2_01_12, EEPType.VLD_OCCUPANCY_ADVANCED: EEPDecoder._decode_d2_06_01,
    EEPType.VLD_WINDOW_ADVANCED: EEPDecoder._decode_d2_06_50, EEPType.VLD_MULTI_TEMP_HUMIDITY_ACCEL: EEPDecoder._decode_d2_14_40,
    EEPType.VLD_MULTI_TEMP_HUMIDITY_ACCEL_MAGNET: EEPDecoder._decode_d2_14_41, EEPType.VLD_OCCUPANCY_SIMPLE: EEPDecoder._decode_d2_06_00,
    EEPType.VLD_DESK_OCCUPANCY: EEPDecoder._decode_d2_06_02, EEPType.VLD_PEOPLE_COUNTER: EEPDecoder._decode_d2_06_03,
}