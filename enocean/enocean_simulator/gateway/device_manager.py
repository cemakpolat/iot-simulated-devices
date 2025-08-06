# File: gateway/device_manager.py
from typing import Dict, List, Optional
from devices.virtual_device import VirtualDevice
from protocol.enums import EEPType


class DeviceManager:
    """Manages virtual devices within the gateway - COMPLETE VERSION"""

    def __init__(self):
        self.devices: Dict[str, VirtualDevice] = {}  # name -> device
        self.sender_id_map: Dict[bytes, VirtualDevice] = {}  # sender_id -> device

    def add_device(self, name: str, sender_id: bytes, eep_type: EEPType, base_telegram: bytes = None, interval: float = 5.0) -> bool:
        """Add a new virtual device"""
        try:
            if name in self.devices:
                print(f"[DeviceManager] Device '{name}' already exists")
                return False

            if sender_id in self.sender_id_map:
                existing = self.sender_id_map[sender_id]
                print(f"[DeviceManager] Sender ID {sender_id.hex()} already used by '{existing.name}'")
                return False

            # Generate base telegram if not provided
            if base_telegram is None:
                base_telegram = self._generate_base_telegram(eep_type, sender_id)

            device = VirtualDevice(name, sender_id, eep_type, base_telegram, interval)
            self.devices[name] = device
            self.sender_id_map[sender_id] = device

            print(f"[DeviceManager] Added device '{name}' (ID: {sender_id.hex()}, EEP: {eep_type.value})")
            return True

        except Exception as e:
            print(f"[DeviceManager] Error adding device '{name}': {e}")
            return False

    def remove_device(self, name: str) -> bool:
        """Remove a device by name"""
        if name not in self.devices:
            print(f"[DeviceManager] Device '{name}' not found")
            return False

        device = self.devices[name]
        del self.devices[name]
        del self.sender_id_map[device.sender_id]
        print(f"[DeviceManager] Removed device '{name}'")
        return True

    def get_device_by_name(self, name: str) -> Optional[VirtualDevice]:
        """Get device by name"""
        return self.devices.get(name)

    def get_device_by_sender_id(self, sender_id: bytes) -> Optional[VirtualDevice]:
        """Get device by sender ID"""
        return self.sender_id_map.get(sender_id)

    def get_all_devices(self) -> List[VirtualDevice]:
        """Get all devices"""
        return list(self.devices.values())

    def get_ready_devices(self) -> List[VirtualDevice]:
        """Get devices that are ready to transmit"""
        return [device for device in self.devices.values() if device.should_transmit()]

    def get_device_count(self) -> int:
        """Get total number of devices"""
        return len(self.devices)

    def list_devices(self) -> List[Dict]:
        """List all devices with their info"""
        return [
            {
                'name': device.name,
                'sender_id': device.get_sender_id_hex(),
                'eep_type': device.eep_type.value,
                'interval': device.interval,
                'last_transmission': device.last_transmission
            }
            for device in self.devices.values()
        ]

    def _generate_base_telegram(self, eep_type: EEPType, sender_id: bytes) -> bytes:
        """Generate a base telegram for ALL 82 device types"""
        from protocol.esp3 import ESP3Protocol

        # COMPLETE EEP CONFIGURATION - All 82 device types
        eep_config = {
            # Environmental Sensors - A5 type (4 data bytes)
            EEPType.TEMPERATURE: (0xA5, b'\x12\x34\x56\x08'),
            EEPType.TEMPERATURE_RANGE: (0xA5, b'\x12\x34\x56\x08'),
            EEPType.HUMIDITY: (0xA5, b'\x40\x00\x00\x08'),
            EEPType.TEMPERATURE_HUMIDITY: (0xA5, b'\x50\x30\x08\x08'),
            EEPType.TEMPERATURE_ILLUMINANCE: (0xA5, b'\x12\x34\x56\x08'),
            EEPType.TEMPERATURE_ILLUMINANCE_HUMIDITY: (0xA5, b'\x28\xcb\xaf\x08'),
            EEPType.BAROMETRIC: (0xA5, b'\x40\xda\x00\x08'),
            EEPType.TEMP_HUMIDITY_BAROMETRIC: (0xA5, b'\x50\x30\x08\x08'),
            EEPType.CO2_SENSOR: (0xA5, b'\x00\x3f\x00\x08'),
            EEPType.AIR_QUALITY: (0xA5, b'\x00\x29\x00\x08'),
            EEPType.VOC_SENSOR: (0xA5, b'\x00\x36\x00\x08'),

            # Light and Illuminance Sensors - A5 type
            EEPType.LIGHT_SENSOR: (0xA5, b'\x00\xd6\x00\x08'),
            EEPType.LIGHT_SENSOR_ILLUMINANCE: (0xA5, b'\x00\xd9\x00\x08'),
            EEPType.LIGHT_SENSOR_TEMP_ILLUMINANCE: (0xA5, b'\x68\xcf\x00\x08'),
            EEPType.LIGHT_SENSOR_OCCUPANCY: (0xA5, b'\x00\x97\x78\x08'),

            # Motion and Occupancy Sensors - A5 type
            EEPType.MOTION_SENSOR: (0xA5, b'\x00\x08\x78\x08'),
            EEPType.MOTION_TEMP_SENSOR: (0xA5, b'\x12\xd9\x78\x08'),
            EEPType.MOTION_TEMP_ILLUMINANCE_SENSOR: (0xA5, b'\x2e\xbe\x78\x08'),

            # Specialized Sensors - A5 type
            EEPType.ACCELEROMETER: (0xA5, b'\x7f\x7f\x7f\x08'),
            EEPType.SOIL_MOISTURE: (0xA5, b'\x00\x60\x00\x08'),
            EEPType.RAIN_SENSOR: (0xA5, b'\x00\x08\x78\x08'),

            # Contact and Security Sensors - D5 type (1 data byte)
            EEPType.CONTACT: (0xD5, b'\x08'),
            EEPType.WINDOW_HANDLE: (0xD5, b'\x00'),
            EEPType.DOOR_HANDLE: (0xD5, b'\x00'),
            EEPType.MECHANICAL_HANDLE: (0xF6, b'\x00'),

            # Security Detectors - A5 type
            EEPType.SMOKE_DETECTOR: (0xA5, b'\x00\x08\x00\x08'),
            EEPType.GLASS_BREAK_DETECTOR: (0xA5, b'\x00\x08\x00\x08'),
            EEPType.VIBRATION_DETECTOR: (0xA5, b'\x00\x08\x00\x08'),
            EEPType.FLOOD_DETECTOR: (0xA5, b'\x00\x08\x00\x08'),

            # Switches and Controls - F6 type (1 data byte)
            EEPType.ROCKER_SWITCH: (0xF6, b'\x00'),
            EEPType.ROCKER_SWITCH_2: (0xF6, b'\x00'),
            EEPType.PUSHBUTTON: (0xF6, b'\x00'),
            EEPType.PUSHBUTTON_LATCHING: (0xF6, b'\x00'),
            EEPType.DUAL_PUSHBUTTON: (0xF6, b'\x00'),
            EEPType.ENERGY_HARVESTING_SWITCH: (0xF6, b'\x00'),

            # HVAC and Climate Control - A5 type
            EEPType.RADIATOR_THERMOSTAT: (0xA5, b'\x50\x30\x08\x08'),
            EEPType.RADIATOR_THERMOSTAT_WITH_FEEDBACK: (0xA5, b'\x50\x30\x08\x08'),
            EEPType.FAN_COIL_THERMOSTAT: (0xA5, b'\x50\x30\x08\x08'),
            EEPType.FLOOR_HEATING_THERMOSTAT: (0xA5, b'\x20\x08\x00\x08'),
            EEPType.HVAC_CONTROL: (0xA5, b'\x50\x30\x00\x08'),
            EEPType.SINGLE_ACTUATOR: (0xA5, b'\x00\x00\x00\x08'),

            # Energy and Metering - A5 type
            EEPType.MULTI_SENSOR: (0xA5, b'\x12\x08\x00\x08'),
            EEPType.SOLAR_CELL: (0xA5, b'\x00\x00\x00\x08'),
            EEPType.ENERGY_METER: (0xA5, b'\x00\x00\x08\x08'),
            EEPType.GAS_METER: (0xA5, b'\x00\x00\x08\x08'),
            EEPType.WATER_METER: (0xA5, b'\x00\x00\x08\x08'),
            EEPType.ELECTRICITY_METER: (0xA5, b'\x00\x00\x08\x08'),

            # Lighting Controls - D2 type (variable data bytes)
            EEPType.DIMMER: (0xD2, b'\x50'),
            EEPType.DIMMER_2: (0xD2, b'\x50\x00'),
            EEPType.LED_CONTROLLER: (0xD2, b'\x50'),
            EEPType.RGB_CONTROLLER: (0xD2, b'\x80\x40\x20'),
            EEPType.RGBW_CONTROLLER: (0xD2, b'\x80\x40\x20\x00'),

            # Industrial and Automation - D2 type
            EEPType.ANALOG_INPUT: (0xD2, b'\x80'),
            EEPType.ANALOG_OUTPUT: (0xD2, b'\x80'),
            EEPType.TEMPERATURE_SETPOINT: (0xD2, b'\x80'),
            EEPType.RELATIVE_HUMIDITY_SETPOINT: (0xD2, b'\x80'),
            EEPType.AIR_FLOW_SETPOINT: (0xD2, b'\x80'),
            EEPType.IO_MODULE: (0xD2, b'\x00'),
            EEPType.VALVE_CONTROL: (0xD2, b'\x50'),
            EEPType.PUMP_CONTROL: (0xD2, b'\x50'),

            # Vehicle and Transportation - D2 type
            EEPType.VEHICLE_SENSOR: (0xD2, b'\x50\x50'),
            EEPType.TIRE_PRESSURE: (0xD2, b'\x50\x20'),

            # Communication and Infrastructure - C5 type
            EEPType.GATEWAY: (0xC5, b'\x00\x50'),
            EEPType.REPEATER: (0xC5, b'\x50\x00'),
            EEPType.TIME_SERVER: (0xC5, b'\x00\x00'),
            EEPType.CONFIGURATION_TOOL: (0xC5, b'\x01\x00'),

            # Smart ACK and Security - A7/30 types
            EEPType.SMART_ACK_CLIENT: (0xA7, b'\x00\x00'),
            EEPType.SMART_ACK_GATEWAY: (0xA7, b'\x00\x00'),
            EEPType.SECURE_DEVICE: (0x30, b'\x01\x00'),
            EEPType.SECURE_RETRANSMITTER: (0x30, b'\x01\x00'),

            # UTE (Universal Telegram) Devices - D4 type
            EEPType.UTE_SENSOR: (0xD4, b'\x01\x00'),
            EEPType.UTE_ACTUATOR: (0xD4, b'\x02\x50'),
            EEPType.UTE_SWITCH: (0xD4, b'\x01\x00'),

            # VLD (Variable Length Data) Devices - D2 type
            EEPType.VLD_TEMP_HUMIDITY: (0xD2, b'\x12\x50'),
            EEPType.VLD_OCCUPANCY_ADVANCED: (0xD2, b'\x00\x50'),
            EEPType.VLD_WINDOW_ADVANCED: (0xD2, b'\x00\x00'),
            EEPType.VLD_MULTI_TEMP_HUMIDITY_ACCEL: (0xD2, b'\x12\x50\x7f'),
            EEPType.VLD_MULTI_TEMP_HUMIDITY_ACCEL_MAGNET: (0xD2, b'\x12\x50\x7f\x50'),
            EEPType.VLD_OCCUPANCY_SIMPLE: (0xD2, b'\x00'),
            EEPType.VLD_DESK_OCCUPANCY: (0xD2, b'\x01\x00'),
            EEPType.VLD_PEOPLE_COUNTER: (0xD2, b'\x00\x00'),

            # Manufacturer Specific - FF type
            EEPType.MANUFACTURER_SPECIFIC: (0xFF, b'\x00\x00'),
        }

        if eep_type in eep_config:
            rorg, data = eep_config[eep_type]
            return ESP3Protocol.create_telegram(rorg, data, sender_id, 0x30)
        else:
            # Default telegram for unknown types
            print(f"[DeviceManager] Warning: Unknown EEP type {eep_type}, using default A5 telegram")
            return ESP3Protocol.create_telegram(0xA5, b'\x00\x00\x00\x08', sender_id, 0x30)