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
      const notificationTitle = payload.notification.title || 'Background Message Title';
      const notificationOptions = {
        body: payload.notification.body,
        icon: '/firebase-logo.png'
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


app.get('/', (req, res) => {
  res.sendFile(path.join(STATIC_FILES_DIR, 'index.html'));
});

app.listen(PORT, '0.0.0.0',() => {
  console.log(`FCM Web Client server running at http://localhost:${PORT}`);
  console.log(`Serving static files from: ${STATIC_FILES_DIR}`);
});