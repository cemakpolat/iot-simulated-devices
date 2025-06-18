// Save this as public/firebase-messaging-sw.js
// This file must be in the root of your public directory


importScripts('https://www.gstatic.com/firebasejs/11.9.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.9.0/firebase-messaging-compat.js');



// Your Firebase config (same as in your main app)
const firebaseConfig = {
  apiKey: "AIzaSyDxLauHnLzSboXS760VUS0bJmx3bVzgceg",
  authDomain: "coap-notifier.firebaseapp.com",
  projectId: "coap-notifier",
  storageBucket: "coap-notifier.firebasestorage.app",
  messagingSenderId: "307040982922",
  appId: "1:307040982922:web:41967daf2f7f9fecf15a73"
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  
  // Customize notification here
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/firebase-logo.png', // Optional: add your icon
    badge: '/badge.png',         // Optional: add your badge
    tag: 'smart-thermostat',     // Group notifications
    requireInteraction: true,    // Keep notification until user interacts
    actions: [                   // Optional: add action buttons
      {
        action: 'view',
        title: 'View Details'
      },
      {
        action: 'dismiss',
        title: 'Dismiss'
      }
    ]
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification clicks
self.addEventListener('notificationclick', function(event) {
  console.log('[firebase-messaging-sw.js] Notification clicked', event);
  
  event.notification.close();
  
  if (event.action === 'view') {
    // Open your app
    event.waitUntil(
      clients.openWindow('http://localhost:3011') // Your frontend URL
    );
  } else if (event.action === 'dismiss') {
    // Just close the notification
    return;
  } else {
    // Default click action
    event.waitUntil(
      clients.openWindow('http://localhost:3011')
    );
  }
});