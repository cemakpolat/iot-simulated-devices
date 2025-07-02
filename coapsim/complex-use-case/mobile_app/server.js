const express = require('express');
const axios = require('axios');
const jwt = require('jsonwebtoken');
const path = require('path');
const cors = require('cors');
require('dotenv').config();

const PORT = process.env.PORT || 3000;
const STATIC_FILES_DIR = path.join(__dirname, 'public');

// Fix Docker networking - if AI_CONTROLLER_API_URL points to localhost, use container name
let AI_CONTROLLER_API_BASE_URL = process.env.AI_CONTROLLER_API_URL || "http://localhost:8000";
if (AI_CONTROLLER_API_BASE_URL.includes('localhost')) {
  console.log('⚠️  AI_CONTROLLER_API_URL points to localhost, assuming Docker environment...');
  AI_CONTROLLER_API_BASE_URL = "http://ai-controller:8000";
  console.log(`📡 Using Docker container name: ${AI_CONTROLLER_API_BASE_URL}`);
}

const JWT_SECRET = process.env.JWT_SECRET || "your-secret-key";

const app = express();

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors());
app.use(express.static(STATIC_FILES_DIR));

// Logging middleware
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  const authHeader = req.headers.authorization ? req.headers.authorization.substring(0, 20) + '...' : 'none';
  console.log(`[${timestamp}] ${req.method} ${req.url} - Auth: ${authHeader}`);
  
  // Log request body for POST requests (but hide sensitive data)
  if (req.method === 'POST' && req.body) {
    const logBody = { ...req.body };
    if (logBody.password) logBody.password = '[HIDDEN]';
    console.log('Request body:', JSON.stringify(logBody, null, 2));
  }
  
  next();
});

// Simple token pass-through middleware (since AI Controller handles validation)
const passAuthToken = (req, res, next) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' });
  }

  const token = authHeader.substring(7);
  console.log('Passing through token:', token.substring(0, 20) + '...');
  
  // Just pass the token through - let AI Controller validate it
  req.user = { token }; // Store token for reference
  next();
};

// Helper function to forward requests to AI Controller
const forwardToAIController = async (endpoint, method = 'GET', data = null, headers = {}) => {
  const url = `${AI_CONTROLLER_API_BASE_URL}${endpoint}`;
  console.log(`[FORWARD] ${method} request to: ${url}`);
  
  try {
    const config = {
      method,
      url,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...headers
      },
      timeout: 15000,
      validateStatus: (status) => status < 500 // Don't throw on 4xx errors
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      config.data = data;
      console.log('[FORWARD] Request payload:', JSON.stringify(data, null, 2));
    }


    const response = await axios(config);
    
    // Handle different response formats
    if (response.status >= 400) {
      const errorData = response.data || {};
      const errorMessage = errorData.detail || errorData.error || errorData.message || `HTTP ${response.status}`;
      throw new Error(`AI Controller error: ${response.status} - ${errorMessage}`);
    }
    
    // Ensure we have valid data
    if (response.data === null || response.data === undefined) {
      console.warn('[FORWARD] AI Controller returned null/undefined data');
      return {}; // Return empty object instead of null
    }
    
    return response.data;
  } catch (error) {
    console.error(`[FORWARD] Error forwarding to AI Controller (${url}):`, {
      message: error.message,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      code: error.code,
      isAxiosError: error.isAxiosError
    });
    
    if (error.response) {
      // The request was made and the server responded with a status code
      const errorData = error.response.data || {};
      const errorMessage = errorData.detail || errorData.error || errorData.message || 'Unknown error';
      throw new Error(`AI Controller error: ${error.response.status} - ${errorMessage}`);
    } else if (error.code === 'ECONNABORTED') {
      throw new Error('AI Controller response timed out');
    } else if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
      throw new Error(`Failed to connect to AI Controller at ${AI_CONTROLLER_API_BASE_URL}: Connection refused. Check if AI Controller is running and accessible.`);
    } else if (error.code === 'EHOSTUNREACH') {
      throw new Error(`Failed to connect to AI Controller at ${AI_CONTROLLER_API_BASE_URL}: Host unreachable. Check network configuration.`);
    } else {
      throw new Error(`Failed to connect to AI Controller: ${error.message}`);
    }
  }
};

// Environment configuration endpoint
app.get('/mobile/env.js', (req, res) => {
  res.type('application/javascript');
  
  let backendUrl = process.env.BACKEND_URL;
  if (!backendUrl || backendUrl.includes('localhost') || backendUrl.includes('node-app') || backendUrl.includes('thermostat-app')) {
    backendUrl = ''; // This will make client use current page origin
  }
  
  console.log('Serving env.js with BACKEND_URL:', backendUrl || 'current page origin');
  
  res.send(`window.env = ${JSON.stringify({
    FCM_API_KEY: process.env.FCM_API_KEY,
    FCM_PROJECT_ID: process.env.FCM_PROJECT_ID,
    FCM_AUTH_DOMAIN: process.env.FCM_AUTH_DOMAIN,
    FCM_STORAGE_BUCKET: process.env.FCM_STORAGE_BUCKET,
    FCM_SENDER_ID: process.env.FCM_SENDER_ID,
    FCM_APP_ID: process.env.FCM_APP_ID,
    FCM_VAPID_KEY: process.env.FCM_VAPID_KEY,
    BACKEND_URL: backendUrl
  })}`);
});
// Firebase messaging service worker (CRITICAL - this was missing!)
app.get('/firebase-messaging-sw.js', (req, res) => {
  res.set('Content-Type', 'application/javascript');
  res.send(`
    importScripts('https://www.gstatic.com/firebasejs/11.9.0/firebase-app-compat.js');
    importScripts('https://www.gstatic.com/firebasejs/11.9.0/firebase-messaging-compat.js');

    const firebaseConfig = {
      apiKey: "${process.env.FCM_API_KEY}",
      authDomain: "${process.env.FCM_AUTH_DOMAIN}",
      projectId: "${process.env.FCM_PROJECT_ID}",
      storageBucket: "${process.env.FCM_STORAGE_BUCKET}",
      messagingSenderId: "${process.env.FCM_SENDER_ID}",
      appId: "${process.env.FCM_APP_ID}"
    };

    firebase.initializeApp(firebaseConfig);
    const messaging = firebase.messaging();

    messaging.onBackgroundMessage((payload) => {
      console.log('[firebase-messaging-sw.js] Received background message ', payload);
      const notificationTitle = payload.notification.title || 'Smart Thermostat Alert';
      const notificationOptions = {
        body: payload.notification.body,
        icon: '/thermostat-icon.png',
        badge: '/badge-icon.png',
        tag: 'thermostat-notification'
      };
      self.registration.showNotification(notificationTitle, notificationOptions);
    });

    self.addEventListener('notificationclick', (event) => {
      event.notification.close();
      const urlToOpen = new URL('/', self.location.origin).href;
      event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
          for (let client of clientList) {
            if (client.url === urlToOpen && 'focus' in client) {
              return client.focus();
            }
          }
          if (clients.openWindow) return clients.openWindow(urlToOpen);
        })
      );
    });
  `);
});


// Health check and debug endpoints
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    aiController: AI_CONTROLLER_API_BASE_URL,
    jwtSecret: JWT_SECRET.substring(0, 10) + '...',
    nodeEnv: process.env.NODE_ENV || 'development'
  });
});


// Also add for mobile subdirectory
app.get('/mobile/firebase-messaging-sw.js', (req, res) => {
  res.redirect('/firebase-messaging-sw.js');
});


// Authentication endpoints
app.post('/api/auth/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    
  
    if (!username || !password) {
      console.log('Missing credentials');
      return res.status(400).json({ error: 'Username and password are required' });
    }

    console.log(`AI Controller URL: ${AI_CONTROLLER_API_BASE_URL}`);
    
    // Check if AI Controller is reachable first
    try {
      console.log('Testing AI Controller connectivity...');
      const healthCheck = await axios.get(`${AI_CONTROLLER_API_BASE_URL}/health`, { timeout: 5000 });
      console.log('AI Controller health check successful:', healthCheck.status);
    } catch (healthError) {
      console.error('AI Controller health check failed:', healthError.message);
      console.error('Health error details:', {
        code: healthError.code,
        status: healthError.response?.status,
        message: healthError.message
      });
    }
    
    // Try authentication
    let loginData;
    try {
      console.log('Attempting login with /auth/login...');
      loginData = await forwardToAIController('/auth/login', 'POST', { username, password });
      console.log('Login successful with /auth/login');
    } catch (firstError) {
      console.log('Login failed with /auth/login:', firstError.message);
      console.log('Trying /api/auth/login...');
      try {
        loginData = await forwardToAIController('/api/auth/login', 'POST', { username, password });
        console.log('Login successful with /api/auth/login');
      } catch (secondError) {
        console.error('Both login endpoints failed:');
        console.error('First error (/auth/login):', firstError.message);
        console.error('Second error (/api/auth/login):', secondError.message);
        throw firstError;
      }
    }
    
    
    if (!loginData) {
      throw new Error('AI Controller returned null response');
    }
    
    if (loginData.access_token) {
      console.log('Token received, length:', loginData.access_token.length);
      console.log('Token preview:', loginData.access_token.substring(0, 50) + '...');
      
      // Try to decode the token to understand its structure
      try {
        const decoded = jwt.decode(loginData.access_token);
        console.log('Token decoded successfully:', decoded);
      } catch (decodeError) {
        console.log('Could not decode token:', decodeError.message);
      }
    } else {
      console.warn('No access_token in response');
    }
    
    res.json(loginData);
  } catch (error) {
    
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Invalid credentials' });
    } else if (error.message.includes('404')) {
      res.status(503).json({ error: 'Authentication endpoint not found on AI Controller' });
    } else if (error.message.includes('timeout')) {
      res.status(504).json({ error: 'Authentication service timed out' });
    } else if (error.message.includes('ECONNREFUSED') || error.message.includes('ENOTFOUND')) {
      res.status(503).json({ error: 'Cannot connect to AI Controller. Please check if it is running.' });
    } else {
      res.status(503).json({ error: 'Authentication service unavailable: ' + error.message });
    }
  }
});

// Device status endpoint - Updated with correct AI Controller endpoints
app.get('/api/status/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const authHeader = req.headers.authorization;
    
    
    // Use the correct AI Controller endpoint: /device/status/{device_id}
    const statusData = await forwardToAIController(
      `/device/status/${deviceId}`,
      'GET',
      null,
      authHeader ? { Authorization: authHeader } : {}
    );
    
    console.log('✅ Successfully got device status');
    res.json(statusData);
    
  } catch (error) {
    console.error('❌ Device status error:', error.message);
    
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized - token may be invalid or expired' });
    } else if (error.message.includes('404')) {
      res.status(404).json({ error: 'Device not found' });
    } else if (error.message.includes('timeout')) {
      res.status(504).json({ error: 'Request timed out' });
    } else {
      res.status(500).json({ error: 'Failed to fetch device status: ' + error.message });
    }
  }
});

// Device control endpoint
app.post('/api/control/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const command = req.body;
    const authHeader = req.headers.authorization;
    
    console.log(`✅ Sending control command to device: ${deviceId}`, command);
    
    const controlData = await forwardToAIController(
      `/device/control/${deviceId}`,
      'POST',
      command,
      authHeader ? { Authorization: authHeader } : {}
    );
    
    res.json(controlData);
  } catch (error) {
    console.error('❌ Control command error:', error.message);
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized' });
    } else if (error.message.includes('404')) {
      res.status(404).json({ error: 'Device not found' });
    } else {
      res.status(500).json({ error: 'Failed to send control command: ' + error.message });
    }
  }
});

// Temperature predictions endpoint
app.get('/api/predictions/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const { hours = 6 } = req.query;
    const authHeader = req.headers.authorization;
    
    const predictionsData = await forwardToAIController(
      `/device/predictions/${deviceId}?hours=${hours}`,
      'GET',
      null,
      authHeader ? { Authorization: authHeader } : {}
    );
    
    res.json(predictionsData);
  } catch (error) {
    console.error('❌ Predictions fetch error:', error.message);
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized' });
    } else {
      res.status(500).json({ error: 'Failed to fetch predictions: ' + error.message });
    }
  }
});

// Energy data endpoint
app.get('/api/energy/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const { days = 7 } = req.query;
    const authHeader = req.headers.authorization;
    
    const energyData = await forwardToAIController(
      `/device/energy/${deviceId}?days=${days}`,
      'GET',
      null,
      authHeader ? { Authorization: authHeader } : {}
    );
    
    res.json(energyData);
  } catch (error) {
    console.error('❌ Energy data fetch error:', error.message);
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized' });
    } else {
      res.status(500).json({ error: 'Failed to fetch energy data: ' + error.message });
    }
  }
});

// Maintenance status endpoint
app.get('/api/maintenance/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const authHeader = req.headers.authorization;
    
    const maintenanceData = await forwardToAIController(
      `/device/maintenance/${deviceId}`,
      'GET',
      null,
      authHeader ? { Authorization: authHeader } : {}
    );
    
    res.json(maintenanceData);
  } catch (error) {
    console.error('❌ Maintenance fetch error:', error.message);
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized' });
    } else {
      res.status(500).json({ error: 'Failed to fetch maintenance status: ' + error.message });
    }
  }
});

// Device control endpoint
app.post('/api/control/:deviceId', passAuthToken, async (req, res) => {
  try {
    const { deviceId } = req.params;
    const command = req.body;
    const authHeader = req.headers.authorization;
    
    const controlData = await forwardToAIController(
      `/control/${deviceId}`,
      'POST',
      command,
      { Authorization: authHeader }
    );
    
    res.json(controlData);
  } catch (error) {
    console.error('Control command error:', error.message);
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized' });
    } else if (error.message.includes('404')) {
      res.status(404).json({ error: 'Device not found' });
    } else if (error.message.includes('timeout')) {
      res.status(504).json({ error: 'Request timed out' });
    } else {
      res.status(500).json({ error: 'Failed to send control command' });
    }
  }
});

// Temperature predictions endpoint
app.get('/api/predictions/:deviceId', passAuthToken, async (req, res) => {
  try {
    const { deviceId } = req.params;
    const { hours = 6 } = req.query;
    const authHeader = req.headers.authorization;
    
    const predictionsData = await forwardToAIController(
      `/predictions/${deviceId}?hours=${hours}`,
      'GET',
      null,
      { Authorization: authHeader }
    );
    
    res.json(predictionsData);
  } catch (error) {
    console.error('Predictions fetch error:', error.message);
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized' });
    } else if (error.message.includes('timeout')) {
      res.status(504).json({ error: 'Request timed out' });
    } else {
      res.status(500).json({ error: 'Failed to fetch predictions' });
    }
  }
});

// Energy data endpoint
app.get('/api/energy/:deviceId', passAuthToken, async (req, res) => {
  try {
    const { deviceId } = req.params;
    const { days = 7 } = req.query;
    const authHeader = req.headers.authorization;
    
    const energyData = await forwardToAIController(
      `/energy/${deviceId}?days=${days}`,
      'GET',
      null,
      { Authorization: authHeader }
    );
    
    res.json(energyData);
  } catch (error) {
    console.error('Energy data fetch error:', error.message);
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized' });
    } else if (error.message.includes('timeout')) {
      res.status(504).json({ error: 'Request timed out' });
    } else {
      res.status(500).json({ error: 'Failed to fetch energy data' });
    }
  }
});

// Schedule endpoint
app.post('/api/schedule/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const schedule = req.body;
    const authHeader = req.headers.authorization;
    
    console.log(`⚠️ Schedule endpoint called but not implemented in AI controller yet`);
    
    res.json({
      success: true,
      message: 'Schedule endpoint not yet implemented in AI controller',
      deviceId: deviceId,
      schedule: schedule
    });
  } catch (error) {
    console.error('❌ Schedule set error:', error.message);
    if (error.message.includes('401')) {
      res.status(401).json({ error: 'Unauthorized' });
    } else {
      res.status(500).json({ error: 'Failed to set schedule: ' + error.message });
    }
  }
});

// FCM Device registration endpoint
app.post('/api/register-device', async (req, res) => {
  try {
    const { device_token, platform } = req.body;
    const authHeader = req.headers.authorization;
   // Check if Authorization header exists and has a token
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Authorization token is required and must be a Bearer token' });
    }

    const token = authHeader.split(' ')[1];
    const tokenPayload = jwt.decode(token);

    if (!tokenPayload) {
      return res.status(401).json({ error: 'Invalid or malformed JWT token' });
    }

    const { sub: userId, email, username } = tokenPayload;

    if (!device_token || !platform) {
      return res.status(400).json({ error: 'Device token and platform are required' });
    }


    // Forward to AI controller's FCM registration endpoint
    const registrationData = await forwardToAIController(
      '/notifications/fcm/register',
      'POST',
      {
        token: device_token,
        platform: platform,
        username: username,
        userId: userId, 
        email: email, 
        timestamp: new Date().toISOString()
      },
      authHeader ? { Authorization: authHeader } : {}
    );
    
    console.log(`✅ Device registered: ${device_token.substring(0, 10)}... on ${platform}`);
    res.json(registrationData);
  } catch (error) {
    console.error('❌ Device registration error:', error.message);
    res.status(500).json({ error: 'Failed to register device: ' + error.message });
  }
});

// Test push notification endpoint
app.post('/api/send-push-test/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    const authHeader = req.headers.authorization;
    
    // Forward to AI controller's test notification endpoint
    const testData = await forwardToAIController(
      '/notifications/fcm/test',
      'POST',
      {
        title: 'Test Notification',
        body: 'This is a test notification from Smart Thermostat'
      },
      authHeader ? { Authorization: authHeader } : {}
    );
    
    console.log(`✅ Test push notification sent for user ${userId}`);
    res.json(testData);
  } catch (error) {
    console.error('❌ Test notification error:', error.message);
    res.status(500).json({ error: 'Failed to send test notification: ' + error.message });
  }
});

// FCM registration endpoints (from your original code)
app.post('/register', (req, res) => {
  const { token, platform, userAgent, timestamp, userId, username, email } = req.body;
  
  console.log('FCM Registration received:', {
    userId,
    username,
    platform,
    tokenPreview: token ? token.substring(0, 20) + '...' : 'No token'
  });
  
  // Store the registration (implement your storage logic here)
  res.json({
    success: true,
    message: 'Device registered successfully',
    userId: userId
  });
});

app.post('/unregister', (req, res) => {
  const { token, userId } = req.body;
  
  console.log('FCM Unregistration received:', {
    userId,
    tokenPreview: token ? token.substring(0, 20) + '...' : 'No token'
  });
  
  // Remove the registration (implement your storage logic here)
  res.json({
    success: true,
    message: 'Device unregistered successfully'
  });
});

// Main app route
app.get('/', (req, res) => {
  res.sendFile(path.join(STATIC_FILES_DIR, 'index.html'));
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Smart Thermostat server running at http://localhost:${PORT}`);
  console.log(`AI Controller API: ${AI_CONTROLLER_API_BASE_URL}`);
  console.log(`Serving static files from: ${STATIC_FILES_DIR}`);
});