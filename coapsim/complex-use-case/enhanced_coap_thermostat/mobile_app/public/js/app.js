// ================================
// Application State Management
// ================================
class AppState {
    constructor() {
        this.isAuthenticated = false;
        this.token = localStorage.getItem('auth_token');
        this.selectedDevice = null;
        this.deviceData = null;
        this.fcmConnected = false;
    }

    setAuth(token) {
        this.isAuthenticated = true;
        this.token = token;
        localStorage.setItem('auth_token', token);
    }

    clearAuth() {
        this.isAuthenticated = false;
        this.token = null;
        localStorage.removeItem('auth_token');
    }

    setDevice(deviceId) {
        this.selectedDevice = deviceId;
        localStorage.setItem('selected_device', deviceId);
    }

    getDevice() {
        return this.selectedDevice || localStorage.getItem('selected_device');
    }
}

// ================================
// API Service
// ================================
class APIService {
    constructor(baseUrl, appState) {
        this.baseUrl = this.getApiBaseUrl(baseUrl);
        this.appState = appState;
    }

    getApiBaseUrl(configuredUrl) {
        if (typeof window !== 'undefined') {
            const currentOrigin = window.location.origin;
            if (!configuredUrl || configuredUrl === '') {
                return currentOrigin;
            }
            if (configuredUrl.includes('localhost') && !window.location.hostname.includes('localhost')) {
                return currentOrigin;
            }
            if (configuredUrl.includes('node-app') || configuredUrl.includes('thermostat-app')) {
                return currentOrigin;
            }
        }
        return configuredUrl || '';
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (this.appState.token) {
            config.headers['Authorization'] = `Bearer ${this.appState.token}`;
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    async login(username, password) {
        return this.request('/mobile/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    }

    async getDeviceStatus(deviceId) {
        return this.request(`/mobile/api/status/${deviceId}`);
    }

    async sendControlCommand(deviceId, command) {
        return this.request(`/mobile/api/control/${deviceId}`, {
            method: 'POST',
            body: JSON.stringify(command)
        });
    }

    async registerDevice(deviceToken, platform) {
        return this.request('/mobile/api/register-device', {
            method: 'POST',
            body: JSON.stringify({ device_token: deviceToken, platform })
        });
    }

    async sendTestNotification(userId) {
        return this.request(`/mobile/api/send-push-test/${userId}`, {
            method: 'POST'
        });
    }
}

// ================================
// UI Manager
// ================================
class UIManager {
    constructor() {
        this.elements = {
            authModal: document.getElementById('authModal'),
            mainApp: document.getElementById('mainApp'),
            loginForm: document.getElementById('loginForm'),
            loginError: document.getElementById('loginError'),
            logoutBtn: document.getElementById('logoutBtn'),
            deviceSelect: document.getElementById('deviceSelect'),
            statusCard: document.getElementById('statusCard'),
            connectionStatus: document.getElementById('connectionStatus'),
            connectionText: document.getElementById('connectionText'),
            notificationContainer: document.getElementById('notificationContainer'),
            // Status elements
            currentTemp: document.getElementById('currentTemp'),
            targetTemp: document.getElementById('targetTemp'),
            humidity: document.getElementById('humidity'),
            airQuality: document.getElementById('airQuality'),
            occupancy: document.getElementById('occupancy'),
            energyConsumption: document.getElementById('energyConsumption'),
            deviceStatus: document.getElementById('deviceStatus'),
            hvacStatus: document.getElementById('hvacStatus'),
            // Sensor data
            co2Level: document.getElementById('co2Level'),
            pm25: document.getElementById('pm25'),
            pm10: document.getElementById('pm10'),
            motionDetection: document.getElementById('motionDetection'),
            // Device info
            firmwareVersion: document.getElementById('firmwareVersion'),
            uptime: document.getElementById('uptime'),
            lastMaintenance: document.getElementById('lastMaintenance'),
            deviceId: document.getElementById('deviceId'),
            // Control buttons
            tempUp: document.getElementById('tempUp'),
            tempDown: document.getElementById('tempDown'),
            modeButtons: document.querySelectorAll('.mode-btn'),
            // Notification buttons
            connectNotificationsBtn: document.getElementById('connectNotificationsBtn'),
            testNotificationBtn: document.getElementById('testNotificationBtn'),
            disconnectNotificationsBtn: document.getElementById('disconnectNotificationsBtn')
        };
    }

    showAuth() {
        this.elements.authModal.classList.add('show');
        this.elements.mainApp.classList.add('hidden');
    }

    showMain() {
        this.elements.authModal.classList.remove('show');
        this.elements.mainApp.classList.remove('hidden');
    }

    showError(message) {
        this.elements.loginError.textContent = message;
        this.elements.loginError.classList.remove('hidden');
    }

    hideError() {
        this.elements.loginError.classList.add('hidden');
    }

    updateConnectionStatus(status, text) {
        const statusEl = this.elements.connectionStatus;
        statusEl.className = 'w-2 h-2 rounded-full ';
        
        switch (status) {
            case 'connected':
                statusEl.className += 'bg-google-green-500';
                break;
            case 'connecting':
                statusEl.className += 'bg-google-yellow-500 animate-pulse';
                break;
            case 'error':
                statusEl.className += 'bg-google-red-500';
                break;
            default:
                statusEl.className += 'bg-google-grey-400';
        }
        
        this.elements.connectionText.textContent = text;
    }

    updateDeviceStatus(data) {
        if (!data) return;

        // Temperature
        const tempValue = data.temperature?.value || 0;
        const tempUnit = data.temperature?.unit === 'celsius' ? '°C' : '°F';
        this.elements.currentTemp.textContent = `${tempValue}${tempUnit}`;
        this.elements.targetTemp.textContent = `${data.target_temperature || 0}${tempUnit}`;

        // Basic status
        this.elements.humidity.textContent = `${data.humidity?.value || 0}%`;
        
        // Air quality
        const aqi = data.air_quality?.aqi || 0;
        const quality = data.air_quality?.quality || 'unknown';
        this.elements.airQuality.textContent = `${quality.charAt(0).toUpperCase() + quality.slice(1)} (${aqi})`;

        // Occupancy
        const occupied = data.occupancy?.occupied;
        const motion = data.occupancy?.motion_detected;
        let occupancyText = 'Not Detected';
        if (occupied) occupancyText = 'Occupied';
        else if (motion) occupancyText = 'Motion Detected';
        this.elements.occupancy.textContent = occupancyText;

        // Energy consumption
        this.elements.energyConsumption.textContent = `${(data.energy_consumption || 0).toFixed(1)} kW`;

        // Device status
        this.elements.deviceStatus.textContent = data.status || 'Unknown';
        this.elements.deviceStatus.className = `status-badge ${data.status === 'online' ? 'status-online' : 'status-offline'}`;

        // HVAC status
        const hvacState = data.hvac_state || 'off';
        this.elements.hvacStatus.textContent = hvacState.charAt(0).toUpperCase() + hvacState.slice(1);
        this.elements.hvacStatus.className = `status-badge hvac-${hvacState}`;

        // Sensor data
        this.elements.co2Level.textContent = `${data.air_quality?.co2 || 0} ppm`;
        this.elements.pm25.textContent = `${data.air_quality?.pm2_5 || 0} μg/m³`;
        this.elements.pm10.textContent = `${data.air_quality?.pm10 || 0} μg/m³`;
        this.elements.motionDetection.textContent = motion ? 'Motion Detected' : 'No Motion';

        // Device info
        this.elements.firmwareVersion.textContent = data.firmware_version || 'Unknown';
        this.elements.uptime.textContent = this.formatUptime(data.uptime_seconds || 0);
        this.elements.lastMaintenance.textContent = this.formatTimestamp(data.last_maintenance);
        this.elements.deviceId.textContent = data.device_id || 'Unknown';
    }

    formatUptime(seconds) {
        if (seconds < 60) return `${seconds} seconds`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours`;
        return `${Math.floor(seconds / 86400)} days`;
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        try {
            const date = new Date(timestamp * 1000);
            return date.toLocaleDateString();
        } catch (e) {
            return 'N/A';
        }
    }

    showNotification(title, body, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification-toast material-card p-4 mb-3 border-l-4 ${
            type === 'success' ? 'border-google-green-500 bg-google-green-50' :
            type === 'error' ? 'border-google-red-500 bg-google-red-50' :
            type === 'warning' ? 'border-google-yellow-500 bg-google-yellow-50' :
            'border-google-blue-500 bg-google-blue-50'
        }`;
        
        const iconName = type === 'success' ? 'check_circle' :
                        type === 'error' ? 'error' :
                        type === 'warning' ? 'warning' :
                        'info';
        
        const iconColor = type === 'success' ? 'text-google-green-600' :
                        type === 'error' ? 'text-google-red-600' :
                        type === 'warning' ? 'text-google-yellow-600' :
                        'text-google-blue-600';
        
        notification.innerHTML = `
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0">
                    <span class="material-icons ${iconColor}">${iconName}</span>
                </div>
                <div class="flex-1 min-w-0">
                    <h4 class="text-google-grey-900 font-medium text-sm">${title}</h4>
                    <p class="text-google-grey-700 text-sm mt-1">${body}</p>
                </div>
                <button class="close-btn text-google-grey-400 hover:text-google-grey-600 flex-shrink-0">
                    <span class="material-icons text-lg">close</span>
                </button>
            </div>
        `;
        
        notification.querySelector('.close-btn').addEventListener('click', () => {
            this.removeNotification(notification);
        });
        
        this.elements.notificationContainer.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 100);
        setTimeout(() => this.removeNotification(notification), 5000);
    }

    removeNotification(notification) {
        if (notification && notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }

    showDeviceStatus() {
        this.elements.statusCard.classList.remove('hidden');
    }

    hideDeviceStatus() {
        this.elements.statusCard.classList.add('hidden');
    }

    updateNotificationButtons(connected) {
        if (connected) {
            this.elements.connectNotificationsBtn.classList.add('hidden');
            this.elements.testNotificationBtn.classList.remove('hidden');
            this.elements.disconnectNotificationsBtn.classList.remove('hidden');
        } else {
            this.elements.connectNotificationsBtn.classList.remove('hidden');
            this.elements.testNotificationBtn.classList.add('hidden');
            this.elements.disconnectNotificationsBtn.classList.add('hidden');
        }
    }
}

// ================================
// FCM Manager
// ================================
class FCMManager {
    constructor(apiService, uiManager) {
    this.apiService = apiService;
    this.uiManager = uiManager;
    this.app = null;
    this.messaging = null;
    this.token = null;
    this.isConnected = false;
    this.tokenRefreshInterval = null;
    }

    async initialize() {
    try {
        const firebaseConfig = {
            apiKey: window.env?.FCM_API_KEY,
            authDomain: window.env?.FCM_AUTH_DOMAIN,
            projectId: window.env?.FCM_PROJECT_ID,
            storageBucket: window.env?.FCM_STORAGE_BUCKET,
            messagingSenderId: window.env?.FCM_SENDER_ID,
            appId: window.env?.FCM_APP_ID
        };

        console.log('🔥 Initializing Firebase with config:', {
            projectId: firebaseConfig.projectId,
            apiKey: firebaseConfig.apiKey?.substring(0, 10) + '...',
            messagingSenderId: firebaseConfig.messagingSenderId
        });

        this.app = window.firebaseApp.initializeApp(firebaseConfig);
        this.messaging = window.firebaseMessaging.getMessaging(this.app);
        
        console.log('✅ Firebase initialized successfully');
        return true;
    } catch (error) {
        console.error('❌ FCM initialization error:', error);
        return false;
    }
    }

    async requestPermissionAndGetToken() {
    try {
        console.log('🔔 Requesting notification permission...');
        const permission = await Notification.requestPermission();
        console.log('🔔 Permission result:', permission);
        if (permission === 'granted') {
            console.log('🎯 Getting FCM token with VAPID key:', window.env?.FCM_VAPID_KEY?.substring(0, 20) + '...');
            
            const token = await window.firebaseMessaging.getToken(this.messaging, {
                vapidKey: window.env?.FCM_VAPID_KEY
            });
            
            if (token) {
                console.log('✅ FCM token generated:', token.substring(0, 20) + '...');
                console.log('📏 Token length:', token.length);
                this.token = token;
                return token;
            } else {
                throw new Error('No registration token available - check service worker and VAPID key');
            }
        } else {
            throw new Error(`Notification permission ${permission}`);
        }
    } catch (error) {
        console.error('❌ Token retrieval error:', error);
        throw error;
    }
}

async connect() {
if (this.isConnected) return true;

try {
    console.log('🚀 Starting FCM connection...');
    
    const initialized = await this.initialize();
    if (!initialized) throw new Error('Firebase initialization failed');

    // ✨ CRITICAL: Wait for service worker to be ready
    console.log('⏳ Waiting for service worker...');
    await navigator.serviceWorker.ready;
    console.log('✅ Service worker is ready');

    const token = await this.requestPermissionAndGetToken();
    console.log('📱 Registering device with backend...');
    
    await this.apiService.registerDevice(token, 'web');
    console.log('✅ Device registered successfully');
    
    // Set up message handling
    window.firebaseMessaging.onMessage(this.messaging, (payload) => {
        console.log('📨 Foreground message received:', payload);
        const notification = payload.notification || {};
        this.uiManager.showNotification(
            notification.title || 'Notification',
            notification.body || 'You have a new message',
            'info'
        );
    });
    
    this.isConnected = true;
    this.uiManager.updateNotificationButtons(true);
    this.uiManager.showNotification('Notifications Enabled', 'You will now receive push notifications', 'success');
    
    console.log('🎉 FCM connection completed successfully');
    return true;
} catch (error) {
    console.error('❌ FCM connection error:', error);
    this.uiManager.showNotification('Notification Error', error.message, 'error');
    return false;
}
}

// ✨ NEW: Modern token refresh monitoring
startTokenRefreshMonitoring() {
// Check for token changes every 60 seconds
this.tokenRefreshInterval = setInterval(async () => {
    try {
        const currentToken = await window.firebaseMessaging.getToken(this.messaging, {
            vapidKey: window.env?.FCM_VAPID_KEY
        });
        
        if (currentToken && currentToken !== this.token) {
            console.log('🔄 FCM token changed, updating registration...');
            console.log('Old token:', this.token?.substring(0, 20) + '...');
            console.log('New token:', currentToken.substring(0, 20) + '...');
            
            // Update stored token
            this.token = currentToken;
            
            // Re-register with server
            await this.apiService.registerDevice(currentToken, 'web');
            
            this.uiManager.showNotification(
                'Notifications Refreshed', 
                'Your notification connection has been updated', 
                'info'
            );
        }
    } catch (error) {
        console.error('Token refresh check failed:', error);
        // If we can't get a token, the registration might be invalid
        console.warn('🚨 Token refresh failed, notifications may not work');
    }
}, 60000); // Check every minute
}

stopTokenRefreshMonitoring() {
if (this.tokenRefreshInterval) {
    clearInterval(this.tokenRefreshInterval);
    this.tokenRefreshInterval = null;
}
}

disconnect() {
    this.stopTokenRefreshMonitoring();
    this.isConnected = false;
    this.token = null;
    this.uiManager.updateNotificationButtons(false);
    this.uiManager.showNotification('Notifications Disabled', 'Push notifications have been turned off', 'warning');
}

async sendTestNotification() {
if (!this.isConnected) {
    this.uiManager.showNotification('Not Connected', 'Please enable notifications first', 'warning');
    return;
}

try {
    // Try to refresh token before sending test
    const currentToken = await window.firebaseMessaging.getToken(this.messaging, {
        vapidKey: window.env?.FCM_VAPID_KEY
    });
    
    if (currentToken !== this.token) {
        console.log('🔄 Token updated before test notification');
        this.token = currentToken;
        await this.apiService.registerDevice(currentToken, 'web');
    }
} catch (error) {
    console.warn('Could not refresh token before test:', error);
}

try {
    const userId = 'current-user';
    await this.apiService.sendTestNotification(userId);
    this.uiManager.showNotification('Test Sent', 'Test notification has been sent', 'success');
} catch (error) {
    // ✨ NEW: Handle invalid token responses from server
    if (error.message.includes('invalid') || error.message.includes('token')) {
        console.log('🔄 Server reports invalid token, attempting refresh...');
        try {
            await this.refreshTokenAndRetry();
        } catch (refreshError) {
            this.uiManager.showNotification('Token Refresh Failed', 'Please reconnect notifications', 'error');
        }
    } else {
        this.uiManager.showNotification('Test Failed', error.message, 'error');
    }
}
}

async refreshTokenAndRetry() {
try {
    console.log('🔄 Attempting to refresh FCM token...');
    
    // Get new token
    const newToken = await window.firebaseMessaging.getToken(this.messaging, {
        vapidKey: window.env?.FCM_VAPID_KEY
    });
    
    if (newToken && newToken !== this.token) {
        this.token = newToken;
        await this.apiService.registerDevice(newToken, 'web');
        
        this.uiManager.showNotification(
            'Token Refreshed', 
            'Notification connection restored', 
            'success'
        );
        
        return true;
    } else {
        throw new Error('Could not get new token');
    }
} catch (error) {
    console.error('Token refresh failed:', error);
    throw error;
}
}
}
//================================
// ServiceWorker Manaer
//================================

class ServiceWorkerManager {
async register() {
if ('serviceWorker' in navigator) {
    try {
        const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
        console.log('Firebase Service Worker registered:', registration);
        
        // Wait for the service worker to be ready
        await navigator.serviceWorker.ready;
        console.log('Service Worker is ready');
        
        return registration;
    } catch (err) {
        console.error('Service Worker registration failed:', err);
        
        // Fallback: try the mobile path
        try {
            console.log('Trying fallback service worker...');
            const fallbackReg = await navigator.serviceWorker.register('/mobile/firebase-messaging-sw.js');
            await navigator.serviceWorker.ready;
            return fallbackReg;
        } catch (fallbackErr) {
            console.error('Fallback service worker also failed:', fallbackErr);
            return null;
        }
    }
}
return null;
}
}

//================================
// Main Application Class
// ================================
class ThermostatApp {
    constructor() {
        this.appState = new AppState();
        this.apiService = new APIService(window.env?.BACKEND_URL || '', this.appState);
        this.uiManager = new UIManager();
        this.fcmManager = new FCMManager(this.apiService, this.uiManager);
            this.serviceWorker = new ServiceWorkerManager();
        this.deviceUpdateInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkAuthState();
        this.serviceWorker.register(); // added new dto test
    }

    setupEventListeners() {
        // Auth
        this.uiManager.elements.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        this.uiManager.elements.logoutBtn.addEventListener('click', () => this.handleLogout());

        // Device selection
        this.uiManager.elements.deviceSelect.addEventListener('change', (e) => this.handleDeviceChange(e));

        // Temperature controls
        this.uiManager.elements.tempUp.addEventListener('click', () => this.adjustTemperature(1));
        this.uiManager.elements.tempDown.addEventListener('click', () => this.adjustTemperature(-1));

        // Mode controls
        this.uiManager.elements.modeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.setMode(btn.dataset.mode));
        });

        // Notification controls
        this.uiManager.elements.connectNotificationsBtn.addEventListener('click', () => this.fcmManager.connect());
        this.uiManager.elements.testNotificationBtn.addEventListener('click', () => this.fcmManager.sendTestNotification());
        this.uiManager.elements.disconnectNotificationsBtn.addEventListener('click', () => this.fcmManager.disconnect());
    }

    checkAuthState() {
        if (this.appState.token) {
            this.appState.isAuthenticated = true;
            this.showMainApp();
        } else {
            this.uiManager.showAuth();
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        this.uiManager.hideError();

        const username = this.uiManager.elements.loginForm.username.value;
        const password = this.uiManager.elements.loginForm.password.value;

        try {
            const response = await this.apiService.login(username, password);
            this.appState.setAuth(response.access_token);
            this.showMainApp();
            this.uiManager.showNotification('Welcome!', 'Successfully signed in', 'success');
        } catch (error) {
            this.uiManager.showError(error.message);
        }
    }

    handleLogout() {
        this.appState.clearAuth();
        this.fcmManager.disconnect();
        this.clearDeviceUpdates();
        this.uiManager.showAuth();
        this.uiManager.hideDeviceStatus();
        this.uiManager.showNotification('Signed Out', 'You have been signed out', 'info');
    }

    showMainApp() {
        this.uiManager.showMain();
        this.uiManager.updateConnectionStatus('connected', 'Connected');
        
        const savedDevice = this.appState.getDevice();
        if (savedDevice) {
            this.uiManager.elements.deviceSelect.value = savedDevice;
            this.handleDeviceChange({ target: { value: savedDevice } });
        }
    }

    async handleDeviceChange(e) {
        const deviceId = e.target.value;
        
        if (!deviceId) {
            this.uiManager.hideDeviceStatus();
            this.clearDeviceUpdates();
            return;
        }

        this.appState.setDevice(deviceId);
        this.uiManager.showDeviceStatus();
        await this.loadDeviceData(deviceId);
        this.startDeviceUpdates(deviceId);
    }

    async loadDeviceData(deviceId) {
        try {
            this.uiManager.updateConnectionStatus('connecting', 'Loading device data...');
            
            const status = await this.apiService.getDeviceStatus(deviceId);
            this.appState.deviceData = status;
            this.uiManager.updateDeviceStatus(status);
            
            this.uiManager.updateConnectionStatus('connected', 'Device connected');
        } catch (error) {
            console.error('Failed to load device data:', error);
            this.uiManager.updateConnectionStatus('error', 'Failed to load device');
            this.uiManager.showNotification('Device Error', 'Failed to load device data', 'error');
        }
    }

    startDeviceUpdates(deviceId) {
        this.clearDeviceUpdates();
        this.deviceUpdateInterval = setInterval(() => {
            this.loadDeviceData(deviceId);
        }, 30000);
    }

    clearDeviceUpdates() {
        if (this.deviceUpdateInterval) {
            clearInterval(this.deviceUpdateInterval);
            this.deviceUpdateInterval = null;
        }
    }

    async adjustTemperature(delta) {
        const deviceId = this.appState.selectedDevice;
        if (!deviceId) return;

        try {
            const currentTarget = this.appState.deviceData?.target_temperature || 22;
            const newTarget = currentTarget + delta;
            
            await this.apiService.sendControlCommand(deviceId, {
                action: 'set_temperature',
                target_temperature: newTarget
            });
            
            this.uiManager.showNotification('Temperature Updated', `Target set to ${newTarget}°`, 'success');
            await this.loadDeviceData(deviceId);
        } catch (error) {
            this.uiManager.showNotification('Control Error', 'Failed to adjust temperature', 'error');
        }
    }

    async setMode(mode) {
        const deviceId = this.appState.selectedDevice;
        if (!deviceId) return;

        try {
            await this.apiService.sendControlCommand(deviceId, {
                action: 'set_mode',
                mode: mode
            });
            
            this.uiManager.showNotification('Mode Changed', `Set to ${mode} mode`, 'success');
            await this.loadDeviceData(deviceId);
        } catch (error) {
            this.uiManager.showNotification('Control Error', 'Failed to change mode', 'error');
        }
    }
}

// ================================
// Application Bootstrap
// ================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Smart Thermostat App...');
    const app = new ThermostatApp();
    window.thermostatApp = app;
});