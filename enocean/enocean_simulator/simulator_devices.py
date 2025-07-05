# simulator_devices.py
"""
Device configuration for EnOcean simulator that matches gateway device registry
"""

from protocol.enums import EEPType

# Device configuration that matches the gateway's devices_bk.json
SIMULATOR_DEVICES = [
    # Environmental Sensors - Basic
    {
        "name": "TempSensor_Kitchen",
        "sender_id": bytes.fromhex("789ABC30"),
        "eep_type": EEPType.TEMPERATURE,
        "interval": 300,
        "gateway_profile": "A5-02-01"
    },
    {
        "name": "HumiditySensor_Bathroom",
        "sender_id": bytes.fromhex("789ABC31"),
        "eep_type": EEPType.HUMIDITY,
        "interval": 360,
        "gateway_profile": "A5-10-01"
    },
    {
        "name": "TempHumidity_LivingRoom",
        "sender_id": bytes.fromhex("789ABC32"),
        "eep_type": EEPType.TEMPERATURE_HUMIDITY,
        "interval": 420,
        "gateway_profile": "A5-04-01"
    },
    {
        "name": "CO2Sensor_Office",
        "sender_id": bytes.fromhex("789ABC33"),
        "eep_type": EEPType.CO2_SENSOR,
        "interval": 900,
        "gateway_profile": "A5-09-04"
    },
    {
        "name": "LightSensor_ConferenceRoom",
        "sender_id": bytes.fromhex("789ABC34"),
        "eep_type": EEPType.LIGHT_SENSOR,
        "interval": 600,
        "gateway_profile": "A5-06-01"
    },
    {
        "name": "TempRangeSensor_Warehouse",
        "sender_id": bytes.fromhex("789ABC35"),
        "eep_type": EEPType.TEMPERATURE_RANGE,
        "interval": 480,
        "gateway_profile": "A5-02-02"
    },
    {
        "name": "TempIlluminance_Reception",
        "sender_id": bytes.fromhex("789ABC36"),
        "eep_type": EEPType.TEMPERATURE_ILLUMINANCE,
        "interval": 720,
        "gateway_profile": "A5-02-04"
    },
    {
        "name": "TempHumidityIlluminance_Lobby",
        "sender_id": bytes.fromhex("789ABC37"),
        "eep_type": EEPType.TEMPERATURE_ILLUMINANCE_HUMIDITY,
        "interval": 900,
        "gateway_profile": "A5-02-05"
    },
    {
        "name": "BarometricSensor_WeatherStation",
        "sender_id": bytes.fromhex("789ABC38"),
        "eep_type": EEPType.BAROMETRIC,
        "interval": 1200,
        "gateway_profile": "A5-10-02"
    },
    {
        "name": "TempHumidityBarometric_Outdoor",
        "sender_id": bytes.fromhex("789ABC39"),
        "eep_type": EEPType.TEMP_HUMIDITY_BAROMETRIC,
        "interval": 1500,
        "gateway_profile": "A5-10-03"
    },

    # Motion and Occupancy Sensors
    {
        "name": "MotionSensor_Hallway",
        "sender_id": bytes.fromhex("789ABC3D"),
        "eep_type": EEPType.MOTION_SENSOR,
        "interval": 180,
        "gateway_profile": "A5-07-01"
    },
    {
        "name": "MotionTempSensor_Bathroom",
        "sender_id": bytes.fromhex("789ABC3E"),
        "eep_type": EEPType.MOTION_TEMP_SENSOR,
        "interval": 300,
        "gateway_profile": "A5-07-02"
    },

    # Specialized Sensors
    {
        "name": "Accelerometer_VibrationMonitor",
        "sender_id": bytes.fromhex("789ABC40"),
        "eep_type": EEPType.ACCELEROMETER,
        "interval": 120,
        "gateway_profile": "A5-08-01"
    },
    {
        "name": "SoilMoisture_Garden",
        "sender_id": bytes.fromhex("789ABC43"),
        "eep_type": EEPType.SOIL_MOISTURE,
        "interval": 3600,
        "gateway_profile": "A5-13-02"
    },
    {
        "name": "RainSensor_Outdoor",
        "sender_id": bytes.fromhex("789ABC44"),
        "eep_type": EEPType.RAIN_SENSOR,
        "interval": 600,
        "gateway_profile": "A5-10-09"
    },

    # Contact and Security Sensors
    {
        "name": "ContactSensor_FrontDoor",
        "sender_id": bytes.fromhex("789ABC45"),
        "eep_type": EEPType.CONTACT,
        "interval": 0,  # Event-driven
        "gateway_profile": "D5-00-01"
    },
    {
        "name": "WindowHandle_MasterBedroom",
        "sender_id": bytes.fromhex("789ABC46"),
        "eep_type": EEPType.WINDOW_HANDLE,
        "interval": 0,  # Event-driven
        "gateway_profile": "D5-00-01"
    },
    {
        "name": "DoorHandle_MainEntrance",
        "sender_id": bytes.fromhex("789ABC47"),
        "eep_type": EEPType.DOOR_HANDLE,
        "interval": 0,  # Event-driven
        "gateway_profile": "D5-00-01"
    },

    # Security Detectors
    {
        "name": "SmokeDetector_Kitchen",
        "sender_id": bytes.fromhex("789ABC49"),
        "eep_type": EEPType.SMOKE_DETECTOR,
        "interval": 1800,
        "gateway_profile": "A5-12-01"
    },
    {
        "name": "GlassBreakDetector_LivingRoom",
        "sender_id": bytes.fromhex("789ABC4A"),
        "eep_type": EEPType.GLASS_BREAK_DETECTOR,
        "interval": 0,  # Event-driven
        "gateway_profile": "A5-12-02"
    },
    {
        "name": "VibrationDetector_Safe",
        "sender_id": bytes.fromhex("789ABC4B"),
        "eep_type": EEPType.VIBRATION_DETECTOR,
        "interval": 0,  # Event-driven
        "gateway_profile": "A5-12-03"
    },
    {
        "name": "FloodDetector_Basement",
        "sender_id": bytes.fromhex("789ABC4C"),
        "eep_type": EEPType.FLOOD_DETECTOR,
        "interval": 600,
        "gateway_profile": "A5-13-01"
    },

    # Switches and Controls
    {
        "name": "RockerSwitch_MasterBedroom",
        "sender_id": bytes.fromhex("789ABC50"),
        "eep_type": EEPType.ROCKER_SWITCH,
        "interval": 0,  # Event-driven
        "gateway_profile": "F6-02-01"
    },
    {
        "name": "RockerSwitch2_LivingRoom",
        "sender_id": bytes.fromhex("789ABC51"),
        "eep_type": EEPType.ROCKER_SWITCH_2,
        "interval": 0,  # Event-driven
        "gateway_profile": "F6-02-02"
    },
    {
        "name": "PushButton_Doorbell",
        "sender_id": bytes.fromhex("789ABC52"),
        "eep_type": EEPType.PUSHBUTTON,
        "interval": 0,  # Event-driven
        "gateway_profile": "F6-02-01"
    },
    {
        "name": "DualPushButton_Office",
        "sender_id": bytes.fromhex("789ABC54"),
        "eep_type": EEPType.DUAL_PUSHBUTTON,
        "interval": 0,  # Event-driven
        "gateway_profile": "F6-02-01"
    },

    # HVAC and Climate Control
    {
        "name": "RadiatorThermostat_LivingRoom",
        "sender_id": bytes.fromhex("789ABC60"),
        "eep_type": EEPType.RADIATOR_THERMOSTAT,
        "interval": 1800,
        "gateway_profile": "D2-01-12"
    },
    {
        "name": "FanCoilThermostat_Office",
        "sender_id": bytes.fromhex("789ABC62"),
        "eep_type": EEPType.FAN_COIL_THERMOSTAT,
        "interval": 1800,
        "gateway_profile": "D2-01-12"
    },

    # Energy and Metering
    {
        "name": "MultiSensor_SmartBuilding",
        "sender_id": bytes.fromhex("789ABC70"),
        "eep_type": EEPType.MULTI_SENSOR,
        "interval": 600,
        "gateway_profile": "D2-14-40"
    },
    {
        "name": "EnergyMeter_MainPanel",
        "sender_id": bytes.fromhex("789ABC72"),
        "eep_type": EEPType.ENERGY_METER,
        "interval": 3600,
        "gateway_profile": "D2-01-01"
    },
    {
        "name": "WaterMeter_Utility",
        "sender_id": bytes.fromhex("789ABC74"),
        "eep_type": EEPType.WATER_METER,
        "interval": 3600,
        "gateway_profile": "D2-01-01"
    },

    # Lighting Controls
    {
        "name": "Dimmer_LivingRoom",
        "sender_id": bytes.fromhex("789ABC80"),
        "eep_type": EEPType.DIMMER,
        "interval": 120,
        "gateway_profile": "D2-01-01"
    },
    {
        "name": "LEDController_Office",
        "sender_id": bytes.fromhex("789ABC82"),
        "eep_type": EEPType.LED_CONTROLLER,
        "interval": 180,
        "gateway_profile": "D2-01-01"
    },

    # Industrial and Automation
    {
        "name": "AnalogInput_ProcessControl",
        "sender_id": bytes.fromhex("789ABC90"),
        "eep_type": EEPType.ANALOG_INPUT,
        "interval": 300,
        "gateway_profile": "D2-01-01"
    },
    {
        "name": "TemperatureSetpoint_HVAC",
        "sender_id": bytes.fromhex("789ABC92"),
        "eep_type": EEPType.TEMPERATURE_SETPOINT,
        "interval": 1800,
        "gateway_profile": "D2-01-12"
    },
    {
        "name": "ValveControl_Heating",
        "sender_id": bytes.fromhex("789ABC96"),
        "eep_type": EEPType.VALVE_CONTROL,
        "interval": 3600,
        "gateway_profile": "D2-05-00"
    },

    # VLD (Variable Length Data) Devices
    {
        "name": "VLDTempHumidity_Server",
        "sender_id": bytes.fromhex("789ABCE0"),
        "eep_type": EEPType.VLD_TEMP_HUMIDITY,
        "interval": 600,
        "gateway_profile": "D2-01-12"
    },
    {
        "name": "VLDOccupancyAdvanced_Conference",
        "sender_id": bytes.fromhex("789ABCE1"),
        "eep_type": EEPType.VLD_OCCUPANCY_ADVANCED,
        "interval": 300,
        "gateway_profile": "D2-14-40"
    },
    {
        "name": "MultiSensor_ConferenceRoom",
        "sender_id": bytes.fromhex("789ABCE3"),
        "eep_type": EEPType.VLD_MULTI_TEMP_HUMIDITY_ACCEL,
        "interval": 900,
        "gateway_profile": "D2-14-40"
    },
    {
        "name": "MultiSensorMagnet_Reception",
        "sender_id": bytes.fromhex("789ABCE4"),
        "eep_type": EEPType.VLD_MULTI_TEMP_HUMIDITY_ACCEL_MAGNET,
        "interval": 900,
        "gateway_profile": "D2-14-41"
    },
    {
        "name": "VLDOccupancySimple_Bathroom",
        "sender_id": bytes.fromhex("789ABCE5"),
        "eep_type": EEPType.VLD_OCCUPANCY_SIMPLE,
        "interval": 300,
        "gateway_profile": "D2-14-40"
    },
    {
        "name": "VLDDeskOccupancy_Workstation",
        "sender_id": bytes.fromhex("789ABCE6"),
        "eep_type": EEPType.VLD_DESK_OCCUPANCY,
        "interval": 600,
        "gateway_profile": "D2-14-40"
    }
]


def create_gateway_device_config():
    """Create a device configuration file for the gateway"""
    config = {
        "version": "1.0",
        "devices": {},
        "locations": {
            "Kitchen": {"building": "Main", "floor": 1, "zone": "residential"},
            "Bathroom": {"building": "Main", "floor": 1, "zone": "residential"},
            "Living Room": {"building": "Main", "floor": 1, "zone": "residential"},
            "Office": {"building": "Main", "floor": 2, "zone": "work"},
            "Bedroom": {"building": "Main", "floor": 2, "zone": "residential"},
            "Front Door": {"building": "Main", "floor": 1, "zone": "security"},
            "Conference Room": {"building": "Main", "floor": 2, "zone": "work"},
            "Reception": {"building": "Main", "floor": 1, "zone": "work"}
        },
        # Add these missing EEP profiles to your eep_profiles dictionary in create_gateway_device_config()

"eep_profiles": {
    # Existing profiles (keep these)
    "A5-02-01": {
        "description": "Temperature sensor -40°C to +40°C",
        "data_length": 4,
        "capabilities": ["temperature"]
    },
    "A5-04-01": {
        "description": "Temperature and humidity sensor",
        "data_length": 4,
        "capabilities": ["temperature", "humidity"]
    },
    "A5-09-04": {
        "description": "CO2 sensor",
        "data_length": 4,
        "capabilities": ["co2"]
    },
    "A5-10-01": {
        "description": "Humidity sensor",
        "data_length": 4,
        "capabilities": ["humidity"]
    },
    "F6-02-01": {
        "description": "Rocker switch",
        "data_length": 1,
        "capabilities": ["switch"]
    },
    "D5-00-01": {
        "description": "Contact sensor",
        "data_length": 1,
        "capabilities": ["contact"]
    },
    "D2-14-40": {
        "description": "Multi-sensor without magnet",
        "data_length": 9,
        "capabilities": ["temperature", "humidity", "acceleration", "illumination"]
    },
    "D2-14-41": {
        "description": "Multi-sensor with magnet contact",
        "data_length": 9,
        "capabilities": ["temperature", "humidity", "acceleration", "illumination", "magnet_contact"]
    },

    # ADD THESE MISSING PROFILES:
    "A5-02-02": {
        "description": "Temperature sensor -30°C to +50°C",
        "data_length": 4,
        "capabilities": ["temperature"]
    },
    "A5-02-04": {
        "description": "Temperature and illuminance sensor",
        "data_length": 4,
        "capabilities": ["temperature", "illuminance"]
    },
    "A5-02-05": {
        "description": "Temperature, humidity and illuminance sensor",
        "data_length": 4,
        "capabilities": ["temperature", "humidity", "illuminance"]
    },
    "A5-06-01": {
        "description": "Light sensor 300-60000 lux",
        "data_length": 4,
        "capabilities": ["illuminance"]
    },
    "A5-07-01": {
        "description": "Motion sensor",
        "data_length": 4,
        "capabilities": ["motion", "supply_voltage"]
    },
    "A5-07-02": {
        "description": "Motion sensor with temperature",
        "data_length": 4,
        "capabilities": ["motion", "temperature", "supply_voltage"]
    },
    "A5-08-01": {
        "description": "Accelerometer",
        "data_length": 4,
        "capabilities": ["acceleration", "supply_voltage"]
    },
    "A5-10-02": {
        "description": "Barometric sensor",
        "data_length": 4,
        "capabilities": ["barometric_pressure", "temperature"]
    },
    "A5-10-03": {
        "description": "Temperature, humidity and barometric sensor",
        "data_length": 4,
        "capabilities": ["temperature", "humidity", "barometric_pressure"]
    },
    "A5-10-09": {
        "description": "Rain sensor",
        "data_length": 4,
        "capabilities": ["rain_detection", "supply_voltage"]
    },
    "A5-12-01": {
        "description": "Smoke detector",
        "data_length": 4,
        "capabilities": ["smoke_detection", "temperature", "supply_voltage"]
    },
    "A5-12-02": {
        "description": "Glass break detector",
        "data_length": 4,
        "capabilities": ["glass_break_detection", "supply_voltage"]
    },
    "A5-12-03": {
        "description": "Vibration detector",
        "data_length": 4,
        "capabilities": ["vibration_detection", "supply_voltage"]
    },
    "A5-13-01": {
        "description": "Flood detector",
        "data_length": 4,
        "capabilities": ["flood_detection", "supply_voltage"]
    },
    "A5-13-02": {
        "description": "Soil moisture sensor",
        "data_length": 4,
        "capabilities": ["soil_moisture", "temperature", "supply_voltage"]
    },
    "F6-02-02": {
        "description": "2-rocker switch",
        "data_length": 1,
        "capabilities": ["switch"]
    },
    "D2-01-01": {
        "description": "Electronic switches and dimmers",
        "data_length": 7,
        "capabilities": ["switching", "dimming", "energy_measurement"]
    },
    "D2-01-12": {
        "description": "Room control panel",
        "data_length": 7,
        "capabilities": ["temperature", "humidity", "setpoint", "fan_speed"]
    },
    "D2-05-00": {
        "description": "Blinds control",
        "data_length": 7,
        "capabilities": ["blinds_position", "blinds_angle"]
    }
}
    }

    # Map locations for devices
    location_map = {
        "TempSensor_Kitchen": "Kitchen",
        "HumiditySensor_Bathroom": "Bathroom",
        "TempHumidity_LivingRoom": "Living Room",
        "CO2Sensor_Office": "Office",
        "RockerSwitch_Bedroom": "Bedroom",
        "ContactSensor_Door": "Front Door",
        "MultiSensor_Conference": "Conference Room",
        "MultiSensorMagnet_Reception": "Reception"
    }

    # Device type mapping
    device_type_map = {
        "A5-02-01": "temperature_sensor",
        "A5-02-02": "temperature_sensor",
        "A5-02-04": "temp_illuminance_sensor",
        "A5-02-05": "temp_humidity_illuminance_sensor",
        "A5-04-01": "temp_humidity_sensor",
        "A5-04-02": "temp_humidity_accel_sensor",
        "A5-06-01": "light_sensor",
        "A5-07-01": "motion_sensor",
        "A5-07-02": "motion_temp_sensor",
        "A5-08-01": "accelerometer",
        "A5-09-01": "gas_sensor",
        "A5-09-04": "co2_sensor",
        "A5-10-01": "humidity_sensor",
        "A5-10-02": "barometric_sensor",
        "A5-10-03": "temp_humidity_barometric_sensor",
        "A5-10-09": "rain_sensor",
        "A5-10-11": "temp_humidity_barometric_sensor",
        "A5-12-01": "smoke_detector",
        "A5-12-02": "glass_break_detector",
        "A5-12-03": "vibration_detector",
        "A5-13-01": "flood_detector",
        "A5-13-02": "test",
        "F6-02-01": "rocker_switch",
        "D5-00-01": "contact_sensor",
        "D2-14-40": "multi_sensor",
        "D2-14-41": "multi_sensor_magnet"
    }

    # Manufacturer mapping
    manufacturer_map = {
        "temperature_sensor": "Eltako",
        "humidity_sensor": "Eltako",
        "temp_humidity_sensor": "Eltako",
        "co2_sensor": "Thermokon",
        "rocker_switch": "Eltako",
        "contact_sensor": "Eltako",
        "multi_sensor": "EnOcean",
        "multi_sensor_magnet": "EnOcean"
    }

    # Model mapping
    model_map = {
        "temperature_sensor": "FTR55D",
        "humidity_sensor": "FHK61",
        "temp_humidity_sensor": "FUTH65D",
        "co2_sensor": "SRC Plus",
        "rocker_switch": "FT55",
        "contact_sensor": "FTK",
        "multi_sensor": "STM550J",
        "multi_sensor_magnet": "STM550J-M"
    }

    # Create device entries
    for device in SIMULATOR_DEVICES:
        sender_id_str = ':'.join(f'{b:02X}' for b in device["sender_id"])
        eep_profile = device["gateway_profile"]
        device_type = device_type_map.get(eep_profile, "unknown")
        location = location_map.get(device["name"], "Unknown")
        manufacturer = manufacturer_map.get(device_type, "Unknown")
        model = model_map.get(device_type, "Unknown")

        # Get capabilities from EEP profile
        capabilities = config["eep_profiles"].get(eep_profile, {}).get("capabilities", [])

        config["devices"][sender_id_str] = {
            "name": device["name"],
            "eep_profile": eep_profile,
            "device_type": device_type,
            "location": location,
            "manufacturer": manufacturer,
            "model": model,
            "description": f"{config['eep_profiles'][eep_profile]['description']}",
            "capabilities": capabilities,
            "interval": device["interval"],
            "last_seen": None,
            "status": "active"
        }

    return config


def save_gateway_config(filename="devices.json"):
    """Save the gateway device configuration to JSON file"""
    import json

    config = create_gateway_device_config()

    with open(filename, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✅ Gateway device configuration saved to {filename}")
    print(f"📊 Created configuration for {len(config['devices'])} devices")

    # Print device summary
    print("\n📋 Device Summary:")
    for sender_id, device in config["devices"].items():
        print(f"   {device['name']} ({sender_id}) -> {device['eep_profile']}")


if __name__ == "__main__":
    # Generate the gateway configuration file
    save_gateway_config()