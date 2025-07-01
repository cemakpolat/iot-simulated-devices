# Smart Thermostat Web Interface

A modern, responsive web interface for smart thermostat control and monitoring, built with Node.js, Firebase Cloud Messaging, and Google Material Design principles.

![Smart Thermostat Interface](https://img.shields.io/badge/Status-Production%20Ready-brightgreen) ![Node.js](https://img.shields.io/badge/Node.js-16%2B-green) ![Firebase](https://img.shields.io/badge/Firebase-FCM-orange) ![Docker](https://img.shields.io/badge/Docker-Containerized-blue)

## 🌟 Features

### Real-Time Device Monitoring
- **Live Sensor Data**: Temperature, humidity, air quality (PM2.5, PM10, CO2)
- **Occupancy Detection**: Motion sensors and presence detection
- **System Status**: HVAC state, energy consumption, device health
- **Device Information**: Firmware version, uptime, maintenance schedules

### Smart Controls
- **Temperature Control**: Intuitive temperature adjustment with real-time feedback
- **Mode Management**: Heat, Cool, and Off modes with visual status indicators
- **Quick Actions**: One-tap controls for common operations

### Push Notifications
- **Firebase Cloud Messaging**: Real-time alerts and notifications
- **Smart Filtering**: Contextual notifications to reduce noise
- **Test Capabilities**: Built-in notification testing tools

### Modern UI/UX
- **Google Material Design**: Clean, professional interface following Material Design guidelines
- **Responsive Layout**: Optimized for desktop, tablet, and mobile devices
- **Accessibility**: WCAG compliant with proper contrast and keyboard navigation
- **Real-time Updates**: Live data refresh every 30 seconds

## 🏗️ Architecture

### System Overview
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │◄──►│   Node.js API    │◄──►│  AI Controller  │
│   (Vanilla JS)  │    │    Gateway       │    │   (FastAPI)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Firebase Cloud  │    │    JWT Auth      │    │   PostgreSQL    │
│   Messaging     │    │   & Security     │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Components

#### Frontend (Client-Side)
- **Technology**: Vanilla JavaScript with ES6+ features
- **Styling**: Tailwind CSS with Google Material Design
- **Architecture**: Modular class-based structure
- **State Management**: Centralized AppState class
- **API Communication**: Fetch-based APIService with automatic token handling

#### Backend (Node.js API Gateway)
- **Framework**: Express.js
- **Authentication**: JWT-based security
- **Role**: Proxy/gateway to AI Controller service
- **Features**: Request forwarding, error handling, logging

#### External Dependencies
- **AI Controller**: FastAPI service providing device management APIs
- **Firebase**: Cloud messaging for push notifications
- **Docker**: Containerization for consistent deployments

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ 
- Docker and Docker Compose
- Firebase project with FCM enabled
- Access to AI Controller service

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-org/smart-thermostat-web
cd smart-thermostat-web
```

2. **Install dependencies**
```bash
npm install
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Environment Configuration**
```bash
# Server Configuration
PORT=3000
NODE_ENV=development

# JWT Configuration (must match AI Controller)
JWT_SECRET=your-super-secret-jwt-key-here

# AI Controller API
AI_CONTROLLER_API_URL=http://ai-controller:8000

# Firebase Cloud Messaging
FCM_API_KEY=your-firebase-api-key
FCM_AUTH_DOMAIN=your-project.firebaseapp.com
FCM_PROJECT_ID=your-firebase-project-id
FCM_STORAGE_BUCKET=your-project.appspot.com
FCM_SENDER_ID=your-sender-id
FCM_APP_ID=your-app-id
FCM_VAPID_KEY=your-vapid-key

# Client Configuration
BACKEND_URL=  # Leave empty for Docker environments
```

5. **Start the application**

**Development:**
```bash
npm run dev
```

**Production:**
```bash
npm start
```

**Docker (Recommended):**
```bash
docker-compose up -d
```

## 🐳 Docker Deployment

### Docker Compose Setup

```yaml
version: '3.8'
services:
  smart-thermostat-web:
    build: .
    ports:
      - "3000:3000"
    environment:
      - AI_CONTROLLER_API_URL=http://ai-controller:8000
      - JWT_SECRET=${JWT_SECRET}
      - NODE_ENV=production
    depends_on:
      - ai-controller
    networks:
      - thermostat-network

  ai-controller:
    # Your AI controller service configuration
    networks:
      - thermostat-network

networks:
  thermostat-network:
    driver: bridge
```

### Production Deployment

```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Scale for high availability
docker-compose -f docker-compose.prod.yml up -d --scale smart-thermostat-web=3

# Monitor logs
docker-compose logs -f smart-thermostat-web
```

## 📱 Usage

### Authentication
1. Navigate to the application URL
2. Sign in with your credentials
3. The system will authenticate against the AI Controller

### Device Management
1. **Select Device**: Choose from available thermostats in the dropdown
2. **View Status**: Real-time sensor data and system status
3. **Control Temperature**: Use +/- buttons or set target temperature
4. **Change Modes**: Switch between Heat, Cool, and Off modes

### Notifications
1. **Enable Notifications**: Click "Enable Notifications" button
2. **Grant Permissions**: Allow browser notification permissions
3. **Test Notifications**: Use "Send Test" to verify functionality

## 🔧 API Endpoints

### Authentication
- `POST /api/auth/login` - User authentication
- Returns JWT token for subsequent requests

### Device Control
- `GET /api/status/:deviceId` - Get device status and sensor data
- `POST /api/control/:deviceId` - Send control commands

### Notifications
- `POST /api/register-device` - Register FCM token
- `POST /api/send-push-test/:userId` - Send test notification

### Health & Monitoring
- `GET /api/health` - Basic health check
- `GET /api/debug/ai-controller` - AI Controller connectivity test

## 🛠️ Development

### Project Structure
```
smart-thermostat-web/
├── server.js              # Main Node.js server
├── package.json           # Dependencies and scripts
├── public/
│   ├── index.html         # Main application UI
│   └── assets/           # Static assets
├── docker-compose.yml     # Development Docker setup
├── Dockerfile            # Container configuration
└── README.md            # This file
```

### Code Architecture

#### Frontend Classes
- **AppState**: Manages authentication and application state
- **APIService**: Handles HTTP communication with backend
- **UIManager**: DOM manipulation and user interface updates
- **FCMManager**: Firebase Cloud Messaging integration
- **ThermostatApp**: Main application controller

#### Backend Structure
- **Express Server**: Main application server
- **Authentication Middleware**: JWT token validation
- **API Forwarding**: Proxy requests to AI Controller
- **Error Handling**: Comprehensive error management
- **Logging**: Request/response logging for debugging

### Development Workflow

1. **Start Development Server**
```bash
npm run dev  # Uses nodemon for auto-restart
```

2. **Code Style**
```bash
npm run lint     # Check code style
npm run format   # Auto-format code
```

3. **Testing**
```bash
npm test         # Run unit tests
npm run test:e2e # Run end-to-end tests
```

## 🔒 Security

### Authentication & Authorization
- **JWT Tokens**: Secure token-based authentication
- **Token Forwarding**: Seamless integration with AI Controller
- **Session Management**: Automatic token refresh and logout
- **CORS Protection**: Configured for production security

### Best Practices
- Environment variable configuration for sensitive data
- HTTPS enforcement in production
- Input validation and sanitization
- Rate limiting on API endpoints
- Comprehensive error handling without information disclosure

## 📊 Monitoring & Logging

### Application Monitoring
- Request/response logging with timestamps
- Error tracking with stack traces
- Performance metrics collection
- Health check endpoints for load balancers

### Firebase Analytics
- User engagement tracking
- Feature usage analytics
- Error reporting and crash analytics
- Performance monitoring

## 🚨 Troubleshooting

### Common Issues

#### Authentication Failures
**Problem**: Login returns 503 Service Unavailable
**Solution**: 
- Check AI Controller connectivity
- Verify JWT_SECRET matches between services
- Ensure network connectivity between containers

#### Device Connection Issues
**Problem**: Device status shows "Failed to load device"
**Solution**:
- Verify device exists in AI Controller
- Check device endpoint URLs match AI Controller routes
- Review network connectivity and firewall rules

#### Notification Problems
**Problem**: Push notifications not working
**Solution**:
- Verify Firebase configuration in environment variables
- Check browser notification permissions
- Ensure VAPID key is correctly configured
- Test with browser developer tools

#### Docker Networking Issues
**Problem**: Cannot connect to AI Controller
**Solution**:
- Use container names instead of localhost in AI_CONTROLLER_API_URL
- Ensure containers are on same Docker network
- Check Docker Compose network configuration

### Debug Mode
Enable detailed logging:
```bash
# Set debug environment
DEBUG=smart-thermostat:* npm run dev

# Or in Docker
docker-compose -f docker-compose.debug.yml up
```

### Log Locations
- **Application Logs**: `docker-compose logs smart-thermostat-web`
- **Error Logs**: Check browser console for client-side errors
- **Network Logs**: Use browser Network tab for API debugging

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Commit with clear messages: `git commit -m 'Add amazing feature'`
5. Push to your branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Code Standards
- **JavaScript**: ES6+ with clear variable naming
- **CSS**: Tailwind CSS classes, avoid custom CSS when possible
- **Documentation**: Update README for any new features
- **Testing**: Add tests for new functionality

### Pull Request Process
1. Ensure all tests pass
2. Update documentation
3. Add screenshots for UI changes
4. Request review from maintainers

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Material Design** for design principles and guidelines
- **Firebase** for reliable cloud messaging infrastructure
- **Tailwind CSS** for utility-first CSS framework
- **Express.js** community for excellent middleware ecosystem

## 📞 Support

### Documentation
- [API Documentation](./docs/api.md)
- [Deployment Guide](./docs/deployment.md)
- [Firebase Setup Guide](./docs/firebase-setup.md)

### Community
- **Issues**: [GitHub Issues](https://github.com/your-org/smart-thermostat-web/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/smart-thermostat-web/discussions)
- **Wiki**: [Project Wiki](https://github.com/your-org/smart-thermostat-web/wiki)

### Commercial Support
For enterprise support, custom development, or consulting services, contact: [support@your-company.com](mailto:support@your-company.com)

---

**Built with ❤️ for the Smart Home Community**