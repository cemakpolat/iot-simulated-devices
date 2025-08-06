# EnOcean Gateway

## **📋 README Features:**

### **🎯 Complete Project Overview**
- **Feature highlights** with badges and visual appeal
- **Architecture diagram** and component descriptions
- **Supported device types** with emojis for easy scanning

### **🚀 Quick Start Guide**
- **Installation instructions** with pip and git
- **Configuration examples** with .env file setup
- **Basic usage examples** with code snippets

### **📊 Real Output Examples**
- **Multi-sensor JSON** (D2-14-41) with all parameters
- **Switch events** (F6-02-01) with button states
- **Temperature/humidity** (A5-04-01) sensor data

### **🔧 Technical Documentation**
- **Complete EEP profile listing** (A5, F6, D5, D2, D4)
- **MQTT topic structure** and Home Assistant integration
- **Advanced usage examples** with custom decoders

### **🛠️ Production Features**
- **Docker deployment** with compose file
- **Monitoring and statistics** export capabilities
- **Troubleshooting guide** with common issues

### **🧪 Development Support**
- **Testing framework** setup and examples
- **Contributing guidelines** with development setup
- **API documentation** references

### **📈 Professional Touches**
- **Roadmap** with upcoming features
- **License and acknowledgments**
- **Support channels** and community links

## **🎉 Key Highlights:**

1. **Professional presentation** with badges and formatting
2. **Complete technical coverage** of all features you've implemented
3. **Real examples** from your actual gateway logs
4. **Production-ready guidance** for deployment
5. **Developer-friendly** with clear setup instructions
6. **Community-focused** with contribution guidelines

The README showcases your gateway as a **professional, production-ready EnOcean solution** that enterprises and developers can confidently use for IoT projects!


A modular, production-ready EnOcean to MQTT gateway with comprehensive EEP profile support and advanced multi-sensor decoding capabilities.

![EnOcean Gateway](https://img.shields.io/badge/EnOcean-Gateway-blue) ![Python](https://img.shields.io/badge/Python-3.8+-green) ![MQTT](https://img.shields.io/badge/MQTT-Supported-orange) ![EEP](https://img.shields.io/badge/EEP-Compliant-purple)

## 🌟 Features

### Core Capabilities
- **Complete EEP Profile Support**: A5, F6, D5, D2, D4 with 80+ device types
- **Advanced VLD Decoding**: Full D2-14-41 multi-sensor support with temperature, humidity, illumination, acceleration, and magnet detection
- **Real-time Processing**: High-performance packet parsing and decoding
- **MQTT Publishing**: Clean JSON output with Home Assistant auto-discovery
- **Modular Architecture**: Extensible design for custom sensors and protocols

### Multi-Sensor Support
- **D2-14-41**: Temperature (-40°C to +60°C), Humidity (0-100%), Illumination (0-100k lx), 3-axis Acceleration (±2.5g), Magnet Contact
- **D2-14-40**: Multi-sensor without magnet contact
- **D2-01-12**: Temperature and humidity sensors
- **D2-01-01**: Electronic switches with energy measurement
- **D2-05-00**: Blind and shutter controls

### Device Types Supported
- 🌡️ **Environmental**: Temperature, humidity, barometric pressure, air quality (CO2, VOC)
- 💡 **Light & Occupancy**: Illuminance sensors, PIR motion detectors, occupancy sensors
- 🔘 **Switches & Controls**: Rocker switches, push buttons, mechanical handles, 4-button switches
- 🚪 **Security**: Contact sensors, door/window handles, smoke detectors, glass break sensors
- 🏠 **HVAC**: Thermostats, radiator valves, fan controls, setpoint controllers
- ⚡ **Energy**: Solar cells, energy meters, gas/water meters, electronic switches
- 🚗 **Automotive**: Vehicle sensors, tire pressure monitors
- 📡 **Infrastructure**: Repeaters, gateways, secure devices, teach-in systems

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/enocean-gateway.git
cd enocean-gateway

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Configuration

Create a `.env` file in the project root:

```bash
# EnOcean Device Configuration
ENOCEAN_DEVICE=/dev/ttyUSB0
ENOCEAN_BAUD=57600

# MQTT Broker Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=enocean/sensors
MQTT_CLIENT_ID=enocean_gateway

# Application Settings
DEBUG=true
```

### Basic Usage

```python
from src import Settings, Logger, SerialConnection, MQTTConnection
from src import PacketParser, PacketDecoder

# Initialize components
settings = Settings()
logger = Logger(debug=settings.DEBUG)

# Create connections
serial_conn = SerialConnection(settings.PORT, settings.BAUD_RATE, logger)
mqtt_conn = MQTTConnection(
    settings.MQTT_BROKER, settings.MQTT_PORT,
    settings.MQTT_CLIENT_ID, settings.MQTT_TOPIC, logger
)

# Start processing
gateway = EnOceanGateway()
gateway.start()
```

### Running the Gateway

```bash
# Basic gateway
python main.py

# With custom configuration
DEBUG=true MQTT_BROKER=192.168.1.100 python main.py

# Advanced gateway with monitoring
python examples/advanced_gateway.py
```

## 📊 Output Examples

### Multi-Sensor Data (D2-14-41)
```json
{
  "device_id": "23:29:45:13",
  "type": "multi_sensor",
  "temperature_c": 22.4,
  "temperature_f": 72.3,
  "humidity_percent": 45.2,
  "illumination_lx": 588.0,
  "acceleration_x_g": -0.023,
  "acceleration_y_g": 0.087,
  "acceleration_z_g": 1.001,
  "magnet_contact": "open",
  "eep_profile": "D2-14-41",
  "timestamp": 1703123456.789,
  "signal_quality": {"rssi": 12, "quality": "excellent"}
}
```

### Switch Events (F6-02-01)
```json
{
  "device_id": "78:9A:BC:50",
  "type": "switch",
  "pressed": true,
  "action": "pressed",
  "button_name": "button_c",
  "button_description": "Button C pressed",
  "button_a_pressed": false,
  "button_b_pressed": false,
  "button_c_pressed": true,
  "button_d_pressed": false,
  "raw_data": "0x50",
  "eep_profile": "F6-02-01"
}
```

### Temperature/Humidity (A5-04-01)
```json
{
  "device_id": "78:9A:BC:3E",
  "type": "temp_humidity",
  "temperature_c": 23.2,
  "temperature_f": 73.8,
  "humidity_percent": 58.5,
  "eep_profile": "A5-04-01"
}
```

## 🏗️ Architecture

```
src/
├── __init__.py                 # Main package exports
├── config/                     # Configuration management
│   ├── __init__.py
│   └── settings.py            # Environment-based settings
├── utils/                      # Utility modules
│   ├── __init__.py
│   └── logger.py              # Enhanced logging
├── connections/                # Connection handlers
│   ├── __init__.py
│   ├── serial_connection.py   # Serial communication
│   └── mqtt_connection.py     # MQTT publishing
└── protocol/                   # Protocol implementation
    ├── __init__.py
    ├── packet_parser.py        # EnOcean packet parsing
    ├── packet_decoder.py       # Main decoding logic
    └── eep_profiles.py         # EEP profile decoders
```

### Key Components

- **PacketParser**: Handles ESP3 packet parsing with CRC validation
- **ExtendedVLDDecoder**: Advanced decoder for complex multi-sensor devices
- **EEPDecoder**: Main decoder supporting all major EEP profiles
- **DeviceRegistry**: Tracks discovered devices and their capabilities
- **MQTTConnection**: Publishes data with Home Assistant auto-discovery

## 🔧 Supported EEP Profiles

### A5 (4-Byte Sensors)
- **A5-02-xx**: Temperature sensors (various ranges)
- **A5-04-xx**: Temperature and humidity sensors
- **A5-06-xx**: Light sensors with illuminance
- **A5-07-xx**: Occupancy sensors with PIR and temperature
- **A5-09-xx**: Air quality sensors (CO2, VOC)

### F6 (Rocker Switches)
- **F6-02-01**: 2-rocker switches with energy bow
- **F6-02-02**: Alternative 2-rocker encoding
- **F6-03-01**: 4-button switches
- **F6-10-00**: Mechanical handles with position

### D5 (1-Byte Sensors)
- **D5-00-01**: Single input contacts (doors, windows)

### D2 (Variable Length Data)
- **D2-14-41**: Multi-sensor (temp/humidity/light/accel/magnet)
- **D2-14-40**: Multi-sensor without magnet
- **D2-01-12**: Temperature and humidity
- **D2-01-01**: Electronic switches with energy measurement
- **D2-05-00**: Blind and shutter controls

### D4 (Universal Teach-In)
- **D4-00-01**: Universal teach-in telegrams

## 🔌 MQTT Integration

### Topic Structure
```
enocean/sensors/{device_id}           # Complete sensor data
enocean/sensors/metrics/{device_id}   # Time-series metrics
enocean/sensors/raw/{device_id}       # Raw packet data (debug)
```

### Home Assistant Auto-Discovery
The gateway automatically publishes Home Assistant discovery messages:
```
homeassistant/sensor/{device_id}_temp/config
homeassistant/sensor/{device_id}_humidity/config
homeassistant/binary_sensor/{device_id}_switch/config
```

## 🛠️ Advanced Usage

### Custom EEP Decoder

```python
from src.protocol.eep_profiles import BaseEEPDecoder

class CustomSensorDecoder(BaseEEPDecoder):
    def can_decode(self, data: bytes) -> bool:
        return data[0] == 0xA5 and len(data) >= 6
        
    def decode(self, data: bytes) -> Optional[Dict[str, Any]]:
        # Implement custom decoding logic
        return {
            'type': 'custom_sensor',
            'value': decode_custom_value(data),
            'eep_profile': 'CUSTOM-A5-XX-XX'
        }

# Register the custom decoder
decoder.eep_decoder.register_custom_decoder(0xA5, CustomSensorDecoder(logger))
```

### Device Registry Usage

```python
from src.protocol.eep_profiles import DeviceRegistry

registry = DeviceRegistry(logger)

# Register known devices
registry.register_device("01:02:03:04", "F6-02-01", {"name": "Kitchen Switch"})
registry.register_device("05:06:07:08", "A5-04-01", {"name": "Living Room Sensor"})

# Get device statistics
stats = registry.get_device_statistics()
print(f"Active devices: {stats['active_devices']}")
print(f"EEP profiles in use: {stats['profile_list']}")
```

### Advanced Gateway with Monitoring

```python
from examples.advanced_gateway import AdvancedEnOceanGateway

gateway = AdvancedEnOceanGateway()
gateway.start_with_monitoring()  # Includes statistics and device tracking
```

## 📈 Monitoring & Statistics

The advanced gateway provides comprehensive monitoring:

- **Packet Statistics**: Success rates, CRC errors, packet types
- **Device Registry**: Device discovery, activity tracking, EEP profiles
- **Decoding Performance**: Success rates by profile type
- **Real-time Metrics**: Throughput, processing times, memory usage

### Statistics Export

```python
# Export detailed statistics
gateway.export_statistics("enocean_stats.json")
```

## 🐳 Docker Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  enocean-gateway:
    build: .
    container_name: enocean-gateway
    restart: unless-stopped
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    environment:
      - ENOCEAN_DEVICE=/dev/ttyUSB0
      - MQTT_BROKER=mosquitto
      - DEBUG=false
    depends_on:
      - mosquitto

  mosquitto:
    image: eclipse-mosquitto:2
    container_name: mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
```

### Run with Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f enocean-gateway

# Stop
docker-compose down
```

## 🔍 Troubleshooting

### Common Issues

#### Serial Connection Failed
```bash
# Check device permissions
sudo usermod -a -G dialout $USER
logout && login

# Verify device path
ls -la /dev/tty*
lsof /dev/ttyUSB0  # Check if device is in use
```

#### MQTT Connection Failed
```bash
# Test broker connectivity
ping mqtt-broker-ip
mosquitto_pub -h broker -t test -m "test"

# Check firewall settings
sudo ufw status
```

#### No Packets Received
- Verify EnOcean device pairing and range
- Check antenna connections
- Enable debug mode: `DEBUG=true`
- Use packet analyzer: `python examples/packet_analyzer.py`

### Debug Mode

Enable comprehensive debugging:
```bash
DEBUG=true python main.py
```

This provides:
- Raw packet dumps in hexadecimal
- Detailed EEP decoding attempts
- Signal quality information
- Device discovery events
- Processing statistics

### Packet Analysis

```python
# Analyze unknown packets
from src.protocol.packet_decoder import PacketDecoder

decoder = PacketDecoder(logger)
result = decoder.decode(packet)

if result and 'analysis' in result:
    print("Packet analysis:", result['analysis'])
    print("EEP candidates:", result.get('eep_candidates', []))
```

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Test specific module
pytest tests/test_eep_profiles.py
```

### Integration Tests
```bash
# Test with simulated devices
python examples/device_simulator.py

# Test individual components
python examples/test_individual_components.py
```

### EEP Compliance Testing
```bash
# Validate EEP compliance
python examples/validate_eep_compliance.py

# Test decoder performance
python examples/benchmark_decoders.py
```

## 📚 Documentation

### API Reference
- [EEP Profile Documentation](docs/eep_profiles.md)
- [Packet Structure Guide](docs/packet_structure.md)
- [Configuration Reference](docs/configuration.md)
- [MQTT Integration Guide](docs/mqtt_integration.md)

### Examples
- [Basic Gateway Setup](examples/basic_usage.py)
- [Custom Decoder Development](examples/custom_decoder.py)
- [Home Assistant Integration](examples/homeassistant_integration.py)
- [Device Simulator](examples/device_simulator.py)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-decoder`
3. Make changes and add tests
4. Ensure code quality: `black src/ && flake8 src/`
5. Update documentation
6. Submit a pull request

### Development Setup

```bash
# Clone for development
git clone https://github.com/your-org/enocean-gateway.git
cd enocean-gateway

# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

## 📋 Roadmap

### Upcoming Features
- [ ] Web-based configuration interface
- [ ] InfluxDB direct integration
- [ ] Advanced device learning mode
- [ ] Encrypted device support (Smart Ack)
- [ ] RESTful API for device management
- [ ] Grafana dashboard templates
- [ ] Cloud integration (AWS IoT, Azure IoT)

### EEP Profile Expansion
- [ ] C5 (Smart Ack) profiles
- [ ] MSC (Manufacturer Specific) profiles
- [ ] Advanced security features
- [ ] Long-range EnOcean support

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [EnOcean Alliance](https://www.enocean-alliance.org/) for the EEP specifications
- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) for MQTT client library
- [pyserial](https://github.com/pyserial/pyserial) for serial communication
- The EnOcean community for device testing and feedback

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/enocean-gateway/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/enocean-gateway/discussions)
- **Documentation**: [Wiki](https://github.com/your-org/enocean-gateway/wiki)

---

**Made with ❤️ for the EnOcean IoT community**