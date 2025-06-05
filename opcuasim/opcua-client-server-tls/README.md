
# Industrial OPC UA System

A comprehensive Docker-based Industrial OPC UA system with secure communication, data monitoring, and automated certificate management.

## 🏗️ System Architecture

This system consists of:
- **OPC UA Server**: Secure industrial data server with TLS encryption
- **OPC UA Client**: Automated client for data operations and monitoring
- **OPC UA Client Interactive**: Interactive client for data operations and monitoring
- **InfluxDB**: Time-series database for industrial data storage
- **Telegraf**: Data collection and monitoring agent

## 📋 Prerequisites

- Docker (v20.0 or higher)
- Docker Compose (v2.0 or higher)
- OpenSSL (for certificate generation)
- Bash shell

## 🚀 Quick Start

1. **Clone and navigate to the project directory**
2. **Make the management script executable:**
   ```bash
   chmod +x opc_system.sh
   ```
3. **Start the complete system:**
   ```bash
   ./opc_system.sh start
   ```
The system will automatically:
- Generate SSL/TLS certificates
- Set up environment configuration
- Build and start all Docker containers

## 📁 Project Structure

```
├── opc_system.sh              # Main system management script
├── generate_certificates.sh   # Certificate generation script
├── .env                      # Environment configuration (auto-created)
├── env.example              # Environment template
├── docker-compose.yml       # Docker services configuration
├── certificates/            # SSL/TLS certificates (auto-generated)
├── logs/                   # Application logs
└── README.md               # This file
```

## ⚙️ Configuration

### Environment Variables (.env)

The system uses a comprehensive `.env` file for configuration. Key sections include:

#### InfluxDB Configuration
```bash
DOCKER_INFLUXDB_INIT_MODE=setup
DOCKER_INFLUXDB_INIT_USERNAME=admin
DOCKER_INFLUXDB_INIT_PASSWORD=adminpassword123
DOCKER_INFLUXDB_INIT_ORG=opcua-data-org
DOCKER_INFLUXDB_INIT_BUCKET=opcua-data-bucket
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=opcua-token-123456789
```

#### Server User Credentials
```bash
OP_USER=operator
OP_PASS=op123
ENG_USER=engineer
ENG_PASS=eng456
ADMIN_USER=admin
ADMIN_PASS=admin789
TELEGRAF_USER=telegraf
TELEGRAF_PASS=telegraf123
```

#### Server Configuration
```bash
SERVER_USE_TLS=true
SERVER_URL_NON_SECURE=opc.tcp://0.0.0.0:4840/freeopcua/server/
SERVER_URL_SECURE=opc.tcp://0.0.0.0:4843/freeopcua/server/
SERVER_NAME="My Secure Industrial OPC UA Server"
```

#### Client Configuration
```bash
CLIENT_OPC_SERVER_URL=opc.tcp://opcua-server:4843/freeopcua/server/
CLIENT_OPC_USE_TLS=true
CLIENT_OPC_USERNAME=operator
CLIENT_OPC_PASSWORD=op123
CLIENT_OPC_OPERATION_INTERVAL=5
CLIENT_OPC_MONITORING_ENABLED=true
CLIENT_OPC_AUTO_CONTROL_ENABLED=true
CLIENT_OPC_MAX_RETRIES=10
CLIENT_OPC_RETRY_DELAY=3
```

## 🔐 Certificate Management

### Automatic Certificate Generation

The `generate_certificates.sh` script creates SSL/TLS certificates for secure communication:

```bash
#!/bin/bash
# Automatically generates certificates for the users below:
# - Server (localhost)
# - Client (opcua-client)
# - Telegraf (telegraf)
```

### Certificate Configuration

Certificates are generated with the following structure:
- **Country**: US
- **State**: CA
- **Location**: San Francisco
- **Organization**: Industrial Corp
- **Organizational Units**: Automation, Control Systems, Monitoring
- **Validity**: 365 days

### Manual Certificate Generation

To regenerate certificates manually:
```bash
chmod +x generate_certificates.sh
./generate_certificates.sh
```

## 🛠️ System Management

The `opc_system.sh` script provides comprehensive system management:

### Commands

| Command | Description |
|---------|-------------|
| `start` | Generate certificates, setup environment, and start system |
| `stop` | Stop all running containers |
| `watch` | Watch container logs in real-time |
| `clean` | Remove all containers, volumes, certificates, and logs |
| `help` | Show help message |

### Usage Examples

```bash
# Start the complete system
./opc_system.sh start

# Monitor system logs
./opc_system.sh watch

# Stop the system
./opc_system.sh stop

# Clean everything for fresh start
./opc_system.sh clean
```
## Interactive Client
In case you aim at interacting dynamically with OPC UA server running, you can run the python code under `client` as follows
```bash
   python client_interactive.py
```
It is assumed that you created a virtual environment and installed the `requirements.txt`, as well as adapted the requested parameters if needed. 

## 🔧 Advanced Configuration


### Customizing Certificates

To add new certificates, modify the `CERTIFICATES` array in `generate_certificates.sh`:

```bash
CERTIFICATES=(
    "server:Automation:localhost"
    "client:Control Systems:opcua-client" 
    "telegraf:Monitoring:telegraf"
    "gateway:Network:iot-gateway"  # New certificate
)
```

### Security Settings

- **TLS Encryption**: Enabled by default on port 4843
- **Non-secure**: Available on port 4840 (can be disabled)
- **Authentication**: Multiple user roles (operator, engineer, admin, telegraf)
- **Certificates**: Self-signed certificates with 2048-bit RSA keys

### Performance Tuning

Adjust client operation intervals and retry settings:
```bash
CLIENT_OPC_OPERATION_INTERVAL=5    # Seconds between operations
CLIENT_OPC_MAX_RETRIES=10         # Maximum connection retries
CLIENT_OPC_RETRY_DELAY=3          # Delay between retries
```

## 📊 Monitoring and Logging

### Container Logs
```bash
# Watch all container logs
./opc_system.sh watch

# Or use Docker Compose directly
docker-compose logs -f
```

### InfluxDB Access
- **Web UI**: http://localhost:8086
- **Username**: admin (configurable in .env)
- **Password**: adminpassword123 (configurable in .env)

### Service Status
```bash
# Check service status
docker-compose ps

# Check individual service logs
docker-compose logs opcua-server
docker-compose logs opcua-client
docker-compose logs influxdb
docker-compose logs telegraf
```

## 🔍 Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x opc_system.sh
   chmod +x generate_certificates.sh
   ```

2. **Docker Not Found**
   - Install Docker and Docker Compose
   - Ensure Docker daemon is running

3. **Certificate Generation Fails**
   - Check if OpenSSL is installed
   - Verify write permissions to certificates/ directory

4. **Container Startup Issues**
   ```bash
   # Check container logs
   ./opc_system.sh watch
   
   # Or check specific service
   docker-compose logs [service-name]
   ```

5. **Network Connection Issues**
   - Verify firewall settings
   - Check if ports 4840, 4843, 8086 are available

### Debug Mode

For detailed debugging:
```bash
# Enable Docker Compose verbose logging
COMPOSE_LOG_LEVEL=DEBUG docker-compose up
```

## 🔄 System Lifecycle

### Startup Sequence
1. **Dependency Check**: Verifies Docker and Docker Compose
2. **Certificate Generation**: Creates SSL/TLS certificates
3. **Environment Setup**: Creates directories and .env file
4. **Container Build**: Builds Docker images
5. **Service Start**: Launches all containers in background

### Shutdown Process
```bash
./opc_system.sh stop
```

### Complete Reset
```bash
./opc_system.sh clean
```
This removes all containers, volumes, certificates, logs, and configuration files.

## 📝 Development

### Adding New Services

1. Update `docker-compose.yml`
2. Add environment variables to `.env`
3. Generate certificates if needed (modify `generate_certificates.sh`)
4. Test with `./opc_system.sh start`

### Environment Customization

Copy `env.example` to `.env` and modify:
```bash
cp env.example .env
# Edit .env with your preferred settings
```

## 🔒 Security Considerations

- Change default passwords in production
- Use proper certificate authority for production certificates
- Implement network segmentation
- Regular security updates for Docker images
- Monitor access logs and user activities

## Troubleshootings

For issues and questions:
1. Check the troubleshooting section
2. Review container logs: `./opc_system.sh watch`
3. Verify configuration in `.env` file
4. Ensure all prerequisites are installed

---

**Note**: This system is designed for development and testing. For production deployment, implement additional security measures and use proper certificate authorities.
