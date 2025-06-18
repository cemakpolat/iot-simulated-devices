const express = require('express');
const path = require('path'); 
require('dotenv').config(); 

const PORT = process.env.PORT || 3000; // Use environment variable or default to 3000
const STATIC_FILES_DIR = path.join(__dirname, 'public'); // Directory for your client-side files

const app = express();

app.use(express.static(STATIC_FILES_DIR));

app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');  // Add 'Authorization' if needed
  next();
});

app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next(); // Pass control to the next middleware/route handler
});

app.get('/env.js', (req, res) => {
  res.type('application/javascript');
  res.send(`window.env = ${JSON.stringify({
    FCM_API_KEY: process.env.FCM_API_KEY,
    FCM_PROJECT_ID: process.env.FCM_PROJECT_ID,
    FCM_AUTH_DOMAIN: process.env.FCM_AUTH_DOMAIN,
    FCM_STORAGE_BUCKET: process.env.FCM_STORAGE_BUCKET,
    FCM_SENDER_ID: process.env.FCM_SENDER_ID,
    FCM_APP_ID: process.env.FCM_APP_ID,
    FCM_VAPID_KEY: process.env.FCM_VAPID_KEY,
    BACKEND_URL: process.env.BACKEND_URL
  })}`);
});


app.get('/', (req, res) => {
  res.sendFile(path.join(STATIC_FILES_DIR, 'index.html'));
});

app.listen(PORT, '0.0.0.0',() => {
  console.log(`FCM Web Client server running at http://localhost:${PORT}`);
  console.log(`Serving static files from: ${STATIC_FILES_DIR}`);
});
