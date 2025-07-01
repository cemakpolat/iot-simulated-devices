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
docker-compose up -d

# Access the dashboard
open http://localhost:8080
```

## ✨ Features

- 🤖 **AI-Powered Predictions** - Machine learning for temperature optimization
- 📱 **Multi-Platform Access** - Web dashboard + Mobile API
- 🔔 **Smart Notifications** - FCM push, email, and webhook alerts
- ⚡ **Real-Time Updates** - WebSocket-based live monitoring
- 🛡️ **Production Ready** - JWT auth, rate limiting, monitoring
- 📊 **Analytics** - Time-series data with InfluxDB and Prometheus

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Dashboard  │    │ Mobile API  │    │AI Controller│
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
- **Mobile API**: Authentication, FCM notifications, API gateway  
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
SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Firebase Cloud Messaging (optional)
FCM_PROJECT_ID=your-firebase-project
FCM_SERVICE_ACCOUNT_PATH=/app/firebase-service-account-key.json

# Webhooks (optional)
WEBHOOK_URLS=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

## 🎯 API Examples

```bash
# Register user
curl -X POST "http://localhost:8080/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "secure123"}'

# Control thermostat
curl -X POST "http://localhost:8080/api/v1/devices/smart-thermostat-01/control" \
  -H "Authorization: Bearer JWT_TOKEN" \
  -d '{"target_temperature": 22.5, "mode": "auto"}'

# Get device status
curl "http://localhost:8080/api/v1/devices/smart-thermostat-01/status" \
  -H "Authorization: Bearer JWT_TOKEN"
```

## 🔗 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Web Dashboard** | http://localhost:8080 | Main UI interface |
| **API Docs** | http://localhost:8080/api/v1/docs | Interactive API documentation |
| **FCM Test Client** | http://localhost:3011 | Test push notifications |
| **Prometheus** | http://localhost:9090 | System metrics |
| **RedisInsight** | http://localhost:8003 | Cache monitoring |

## 📊 Monitoring

The system includes comprehensive monitoring:

- **Health Checks**: `/health` and `/api/health` endpoints
- **Metrics**: Prometheus scraping for system metrics
- **Logs**: Structured logging across all services
- **Cache Monitoring**: RedisInsight for cache performance
- **Real-time**: WebSocket updates for live dashboard

## 🚀 Production Deployment

For production use:

1. **Environment**: Update `.env` with production values
2. **SSL**: Configure SSL certificates in nginx
3. **Scaling**: Use `docker-compose.prod.yml` for multiple replicas
4. **Monitoring**: Set up Grafana dashboards and alerting
5. **Security**: Enable firewall rules and VPN access

## 🧪 Development

```bash
# Local development setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run individual services
cd server && python main.py
cd dashboard && python app.py
cd mobile && uvicorn main:app --reload --port 8001
```

## 📁 Project Structure

```
├── server/           # AI Controller (FastAPI)
├── mobile/           # Mobile API Gateway (FastAPI)  
├── dashboard/        # Web Dashboard (Flask)
├── coap_device/      # CoAP Device Simulator
├── client_fcm/       # FCM Test Client
├── nginx/            # Reverse Proxy Configuration
├── monitoring/       # Prometheus Configuration
└── docker-compose.yml
```

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