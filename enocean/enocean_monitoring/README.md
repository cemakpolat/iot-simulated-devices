# EnOcean Gateway

A complete gateway solution for EnOcean simulated sensors and real EnOcean gateways like USB300 along with MQTT, Telegraf, InfluxDB, and Grafana.


## 🏗️ Architecture

```
EnOcean USB or EnOcean Simulator → EnOcean Gateway → WebApp or MQTT → Telegraf → InfluxDB → Grafana
```

**Components:**
- **EnOcean Gateway**: Python script that reads EnOcean packets and publishes to MQTT
- **Web Interface**: EnOcean Gateway Web interface
- **EMQX**: MQTT broker for message routing
- **Telegraf**: Metrics collection and processing
- **InfluxDB**: Time-series database for sensor data
- **Grafana**: Visualization dashboard

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose if it is planned to use telegraf, influxdb and grafana
- EnOcean USB adapter (e.g., USB 300, USB 500) or enocean simulator project
- Linux/macOS (Windows with WSL2)

### Setup
```bash
# Make the setup script executable and run it
cp env.example .env
chmod +x main.sh
./main.sh start
```


## 📊 Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin123 |
| **InfluxDB** | http://localhost:8086 | admin / enocean123 |
| **MQTT** | localhost:11883 | No auth (default) |
| **Web Interface** | localhost:5001 | No auth (default) |



## 📄 License

MIT License - see LICENSE file for details

