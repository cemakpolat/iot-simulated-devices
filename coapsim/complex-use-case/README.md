# 🌡️ Smart Thermostat AI

> AI-powered smart thermostat system with real-time monitoring, predictive control, and multi-platform notifications

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![CoAP](https://img.shields.io/badge/CoAP-IoT_Protocol-orange)](https://tools.ietf.org/html/rfc7252)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Quick Start

```bash
# Clone and start the system
git clone https://github.com/yourusername/smart-thermostat-ai.git
cd smart-thermostat-ai
cp .env.example .env  # Configure your settings
chmod +x main.sh run_commands.sh
./main.sh start
./run_commands.sh
# Access the dashboard
open http://localhost:8080
# Access the mobile app
open http://localhost:8080/mobile/
```

## ✨ Features

- 🤖 **AI-Powered Predictions** - Machine learning for temperature optimization
- 📱 **Multi-Platform Access** - Web dashboard + Mobile App
- 🔔 **Smart Notifications** - FCM push, email, and webhook alerts
- ⚡ **Real-Time Updates** - WebSocket-based live monitoring
- ⚡ **Mobile-App** - REST-based mobile app
- 🛡️ **Production Ready** - JWT auth, monitoring, integrated redis for providing cache responses
- 📊 **Analytics** - Time-series data with InfluxDB and Prometheus

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Dashboard  │    │ Mobile App  │    │AI Controller│
│   (Flask)   │    │ (FastAPI)   │    │ (FastAPI)   │
│  Port 5000  │    │ Port 8001   │    │ Port 8000   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │    NGINX    │
                    │  Port 8080  │
                    └─────────────┘
```

**Core Services:**
- **AI Controller**: CoAP client, ML predictions, device control
- **Mobile App**: Authentication, FCM notifications, API gateway  
- **Dashboard**: Real-time UI with WebSocket updates
- **CoAP Device**: Simulated smart thermostat
- **Databases**: InfluxDB (metrics), PostgreSQL (users), Redis (cache)

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **IoT Protocol** | CoAP (UDP) | Efficient device communication |
| **Backend** | FastAPI + Python | REST APIs and async processing |
| **Frontend** | Flask + WebSocket | Real-time dashboard |
| **ML/AI** | scikit-learn | Temperature prediction models |
| **Databases** | InfluxDB, PostgreSQL, Redis | Time-series, relational, caching |
| **Notifications** | Firebase FCM, SMTP | Push notifications and alerts |
| **Infrastructure** | Docker Compose, Nginx | Containerization and reverse proxy |
| **Monitoring** | Prometheus, RedisInsight | Metrics and observability |

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.9+ (for local development)
- Firebase account (optional, for push notifications)

## ⚙️ Configuration

Create `.env` file with your settings:

```bash
# Email Notifications
# --- AI Controller (Server) Settings ---
COAP_DEVICE_HOST=coap-device # This MUST match the service name for the client in docker-compose.yml
COAP_DEVICE_PORT=5683
COAP_DEVICE_SECURE_PORT=5684
ENABLE_DTLS_SERVER_CLIENT=false
COAP_PSK_IDENTITY=thermostat # MUST match client's PSK_IDENTITY
COAP_PSK_KEY=secretkey123    # MUST match client's PSK_KEY


# InfluxDB Configuration
INFLUXDB_INIT_MODE=setup
INFLUXDB_INIT_USERNAME=admin
INFLUXDB_INIT_PASSWORD=enocean123
INFLUXDB_INIT_ORG=enocean
INFLUXDB_INIT_BUCKET=sensors
INFLUXDB_INIT_ADMIN_TOKEN=admin_token_secret


INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=coap-token-1234567890
INFLUXDB_ORG=coap-data-org
INFLUXDB_BUCKET=coap-data-bucket


REDIS_URL=redis://redis:6379

POLL_INTERVAL=8
ML_RETRAIN_INTERVAL_HOURS=24

# Email Notification Settings (Optional for testing, requires a valid email/app password)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=youremail@gmail.com
EMAIL_PASSWORD=aaaa jjtc fifr sjej 
FROM_EMAIL=youremail@gmail.com  
ALERT_EMAIL=youremail@gmail.com
WEBHOOK_URLS=https://hooks.slack.com/services/T08SX4JAZ41/...

LOG_LEVEL=INFO 

# ===========================================
# Firebase (Please obtain credentials in Firebase Studio by creating web app)
# ===========================================
# Firebase Web Configuration (for frontend app)
FCM_API_KEY=AIzaSyB5...
FCM_AUTH_DOMAIN=coap-notification-ser.firebaseapp.com
FCM_PROJECT_ID=coap-notification-ser
FCM_STORAGE_BUCKET=coap-notification-ser.firebasestorage.app
FCM_SENDER_ID=519009...
FCM_APP_ID=1:51900995...:web:9dbfac0c0fc638422abf85
FCM_VAPID_KEY=BK_sjI5gAe9Dld0QLL6ebsf--lZNNaCUUUhQT7r_...
# Firebase Web Configuration (for backend in AI-controller)
FCM_SERVICE_ACCOUNT_PATH=/app/firebase-service-account-key.json

# FCM Server Configuration
# -----------------------
FCM_SERVER_PORT=5001

# =========================================== 
# Dashboard app
# ===========================================
# --- General Configuration ---
# A strong, random secret key for Flask sessions and security.
FLASK_SECRET_KEY="change-me-to-a-super-secret-and-random-string"
DEBUG_MODE=true # Set to 'false' for production.

# --- Application Network Settings ---
# The host the Flask/SocketIO app will bind to. 0.0.0.0 makes it accessible on the network.
DASHBOARD_APP_HOST=0.0.0.0

# The port the Flask/SocketIO app will run on.
DASHBOARD_APP_PORT=5000


# --- AI Controller Service URLs ---

AI_CONTROLLER_WS_URL=ws://ai-controller:8092
AI_CONTROLLER_CONTROL_URL=http://ai-controller:8000/control/smart-thermostat-01
```

## 🎯 API Examples

```bash
# Register user
curl -X POST "http://localhost:8080/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "secure123"}'

# Control thermostat
curl -X POST "http://localhost:8080/devices/smart-thermostat-01/control" \
  -H "Authorization: Bearer JWT_TOKEN" \
  -d '{"target_temperature": 22.5, "mode": "auto"}'

# Get device status
curl "http://localhost:8080/devices/smart-thermostat-01/status" \
  -H "Authorization: Bearer JWT_TOKEN"
```

`run_command.sh` script shows many API usage examples.

## 🔗 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Web Dashboard** | http://localhost:8080 | Main UI interface |
| **Mobile App** | http://localhost:8080/mobile | Mobile App UI interface |
| **Prometheus** | http://localhost:9090 | System metrics |
| **RedisInsight** | http://localhost:8003 | Cache monitoring |
| **Grafana** | http://localhost:3000 | Grafana |

## 📊 Monitoring

The system includes comprehensive monitoring:

- **Health Checks**: `/health` and `/api/health` endpoints
- **Metrics**: Prometheus scraping for system metrics
- **Logs**: Structured logging across all services
- **Cache Monitoring**: RedisInsight for cache performance
- **Real-time**: WebSocket updates for live dashboard


## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent async framework
- [CoAP](https://tools.ietf.org/html/rfc7252) protocol for efficient IoT communication
- [InfluxDB](https://www.influxdata.com/) for time-series data management
- [Firebase](https://firebase.google.com/) for push notification infrastructure

---

⭐ **Star this repo if you found it helpful!**