// ================================
        // Configuration Module
        // ================================
        class ConfigManager {
            constructor() {
                this.config = {
                    firebaseConfig: {
                        apiKey: window.env?.FCM_API_KEY || "demo-api-key",
                        authDomain: window.env?.FCM_AUTH_DOMAIN || "demo.firebaseapp.com",
                        projectId: window.env?.FCM_PROJECT_ID || "demo-project",
                        storageBucket: window.env?.FCM_STORAGE_BUCKET || "demo.appspot.com",
                        messagingSenderId: window.env?.FCM_SENDER_ID || "123456789",
                        appId: window.env?.FCM_APP_ID || "demo-app-id"
                    },
                    backendUrl: window.env?.BACKEND_URL || "http://localhost:3001",
                    vapidKey: window.env?.FCM_VAPID_KEY || "valid_key_here",
                    defaultNotificationDuration: 5000
                };
            }

            get(key) {
                return this.config[key];
            }

            isDevelopment() {
                return location.hostname === 'localhost' || location.hostname === '127.0.0.1';
            }
        }

        // ================================
        // DOM Elements Manager
        // ================================
        class DOMManager {
            constructor() {
                this.elements = {
                    statusIndicator: document.getElementById('statusIndicator'),
                    statusText: document.getElementById('statusText'),
                    tokenStatus: document.getElementById('tokenStatus'),
                    registrationStatus: document.getElementById('registrationStatus'),
                    durationSlider: document.getElementById('durationSlider'),
                    durationValue: document.getElementById('durationValue'),
                    totalNotifications: document.getElementById('totalNotifications'),
                    lastReceived: document.getElementById('lastReceived'),
                    notificationContainer: document.getElementById('notificationContainer')
                };
            }

            get(elementName) {
                return this.elements[elementName];
            }

            updateText(elementName, text) {
                const element = this.get(elementName);
                if (element) {
                    element.textContent = text;
                }
            }

            updateHTML(elementName, html) {
                const element = this.get(elementName);
                if (element) {
                    element.innerHTML = html;
                }
            }
        }

        // ================================
        // Status Manager
        // ================================
        class StatusManager {
            constructor(domManager) {
                this.dom = domManager;
            }

            update(type, message) {
                this.dom.updateText('statusText', message);
                const indicator = this.dom.get('statusIndicator');
                indicator.className = 'w-3 h-3 rounded-full ';
                
                switch (type) {
                    case 'success':
                        indicator.className += 'bg-green-400';
                        break;
                    case 'warning':
                        indicator.className += 'bg-yellow-400';
                        break;
                    case 'error':
                        indicator.className += 'bg-red-400';
                        break;
                    default:
                        indicator.className += 'bg-blue-400 animate-pulse';
                }
            }

            updateTokenStatus(message) {
                this.dom.updateText('tokenStatus', message);
            }

            updateRegistrationStatus(message) {
                this.dom.updateText('registrationStatus', message);
            }
        }

        // ================================
        // Statistics Manager
        // ================================
        class StatsManager {
            constructor(domManager) {
                this.dom = domManager;
                this.notificationCount = 0;
            }

            incrementNotificationCount() {
                this.notificationCount++;
                this.dom.updateText('totalNotifications', this.notificationCount.toString());
                this.dom.updateText('lastReceived', new Date().toLocaleTimeString());
            }

            getNotificationCount() {
                return this.notificationCount;
            }
        }

        // ================================
        // Notification UI Manager
        // ================================
        class NotificationUIManager {
            constructor(domManager, statsManager) {
                this.dom = domManager;
                this.stats = statsManager;
                this.duration = 5000;
            }

            setDuration(duration) {
                this.duration = duration;
            }

            show(payload) {
                const notification = payload.notification;
                const data = payload.data || {};
                
                const notificationEl = this.createNotificationElement(notification, data);
                this.addToContainer(notificationEl);
                this.stats.incrementNotificationCount();
                this.scheduleRemoval(notificationEl);
            }

            createNotificationElement(notification, data) {
                const notificationEl = document.createElement('div');
                notificationEl.className = 'notification-card rounded-xl p-4 mb-3 notification-enter border-l-4 border-blue-500';
                
                const progressBar = this.createProgressBar();
                
                notificationEl.innerHTML = `
                    <div class="flex items-start space-x-3">
                        <div class="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                            <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"/>
                            </svg>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center justify-between">
                                <h4 class="text-gray-800 font-semibold text-sm truncate">
                                    ${notification?.title || 'Notification'}
                                </h4>
                                <button class="close-btn text-gray-400 hover:text-gray-600 ml-2">
                                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                                    </svg>
                                </button>
                            </div>
                            <p class="text-gray-600 text-sm mt-1">
                                ${notification?.body || 'No message content'}
                            </p>
                            ${data.url ? `<a href="${data.url}" class="text-blue-500 text-xs mt-2 block hover:underline">View Details</a>` : ''}
                        </div>
                    </div>
                `;
                
                notificationEl.style.position = 'relative';
                notificationEl.appendChild(progressBar);
                
                this.attachCloseHandler(notificationEl);
                
                return notificationEl;
            }

            createProgressBar() {
                const progressBar = document.createElement('div');
                progressBar.className = 'absolute bottom-0 left-0 h-1 bg-blue-500 progress-bar rounded-b-xl';
                progressBar.style.setProperty('--duration', `${this.duration}ms`);
                return progressBar;
            }

            attachCloseHandler(notificationEl) {
                const closeBtn = notificationEl.querySelector('.close-btn');
                closeBtn.addEventListener('click', () => {
                    this.remove(notificationEl);
                });
            }

            addToContainer(notificationEl) {
                const container = this.dom.get('notificationContainer');
                container.appendChild(notificationEl);
            }

            scheduleRemoval(notificationEl) {
                setTimeout(() => {
                    this.remove(notificationEl);
                }, this.duration);
            }

            remove(notificationEl) {
                if (notificationEl && notificationEl.parentNode) {
                    notificationEl.classList.remove('notification-enter');
                    notificationEl.classList.add('notification-exit');
                    
                    setTimeout(() => {
                        if (notificationEl.parentNode) {
                            notificationEl.parentNode.removeChild(notificationEl);
                        }
                    }, 300);
                }
            }
        }

        // ================================
        // Firebase Manager
        // ================================
        class FirebaseManager {
            constructor(config, statusManager) {
                this.config = config;
                this.status = statusManager;
                this.app = null;
                this.messaging = null;
                this.token = null;
            }

            async initialize() {
                try {
                    this.app = window.firebaseApp.initializeApp(this.config.get('firebaseConfig'));
                    this.messaging = window.firebaseMessaging.getMessaging(this.app);
                    return true;
                } catch (error) {
                    console.error('Firebase initialization error:', error);
                    this.status.update('error', 'Firebase initialization failed');
                    this.status.updateTokenStatus('Error: ' + error.message);
                    return false;
                }
            }

            async requestPermissionAndGetToken() {
                try {
                    const permission = await Notification.requestPermission();
                    
                    if (permission === 'granted') {
                        const token = await window.firebaseMessaging.getToken(this.messaging, {
                            vapidKey: this.config.get('vapidKey')
                        });
                        
                        if (token) {
                            this.token = token;
                            console.log('FCM Token:', token);
                            this.status.updateTokenStatus('Token received: ' + token.substring(0, 20) + '...');
                            return token;
                        } else {
                            throw new Error('No registration token available');
                        }
                    } else {
                        throw new Error('Notification permission denied');
                    }
                } catch (error) {
                    console.error('Token retrieval error:', error);
                    this.status.update('error', 'Token retrieval failed');
                    this.status.updateTokenStatus('Error: ' + error.message);
                    return null;
                }
            }

            onMessage(callback) {
                if (this.messaging) {
                    window.firebaseMessaging.onMessage(this.messaging, callback);
                }
            }

            getToken() {
                return this.token;
            }
        }

        // ================================
        // Backend Service
        // ================================
        class BackendService {
            constructor(config, statusManager) {
                this.config = config;
                this.status = statusManager;
            }

            async register(token) {
                try {
                    console.log('Registering with backend...');
                    console.log('Backend URL:', this.config.get('backendUrl'));
                    
                    const response = await fetch(`${this.config.get('backendUrl')}/register`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            token: token,
                            platform: 'web',
                            userAgent: navigator.userAgent,
                            timestamp: new Date().toISOString(),
                            user_id: "user1",
                            user_name: "John Doe",
                            user_email:"new user"
                        })
                    });

                    if (response.ok) {
                        const result = await response.json();
                        console.log('Registration successful:', result);
                        this.status.update('success', 'Connected and ready');
                        this.status.updateRegistrationStatus('Successfully registered with backend');
                        return true;
                    } else {
                        throw new Error(`Registration failed: ${response.status}`);
                    }
                } catch (error) {
                    console.error('Backend registration error:', error);
                    this.status.update('warning', 'Ready (backend registration failed)');
                    this.status.updateRegistrationStatus('Warning: Backend registration failed - ' + error.message);
                    return false;
                }
            }
        }

        // ================================
        // Settings Manager
        // ================================
        class SettingsManager {
            constructor(domManager, notificationUI) {
                this.dom = domManager;
                this.notificationUI = notificationUI;
                this.setupEventListeners();
            }

            setupEventListeners() {
                const durationSlider = this.dom.get('durationSlider');
                durationSlider.addEventListener('input', (e) => {
                    const value = parseInt(e.target.value);
                    const duration = value * 1000;
                    this.notificationUI.setDuration(duration);
                    this.dom.updateText('durationValue', value + 's');
                });
            }
        }

        // ================================
        // Service Worker Manager
        // ================================
        class ServiceWorkerManager {
            async register() {
                if ('serviceWorker' in navigator) {
                    try {
                        const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
                        console.log('Service Worker registered:', registration);
                        return registration;
                    } catch (err) {
                        console.error('Service Worker registration failed:', err);
                        return null;
                    }
                }
                return null;
            }
        }

        // ================================
        // Main Application Class
        // ================================
        class FCMApp {
            constructor() {
                this.config = new ConfigManager();
                this.dom = new DOMManager();
                this.status = new StatusManager(this.dom);
                this.stats = new StatsManager(this.dom);
                this.notificationUI = new NotificationUIManager(this.dom, this.stats);
                this.firebase = new FirebaseManager(this.config, this.status);
                this.backend = new BackendService(this.config, this.status);
                this.settings = new SettingsManager(this.dom, this.notificationUI);
                this.serviceWorker = new ServiceWorkerManager();
            }

            async initialize() {
                console.log('App initializing...');
                this.status.update('loading', 'Initializing...');
                
                if (this.config.isDevelopment()) {
                    console.log('Development mode detected');
                }
                
                // Register service worker
                await this.serviceWorker.register();
                
                // Initialize Firebase
                const firebaseInitialized = await this.firebase.initialize();
                if (!firebaseInitialized) {
                    return;
                }
                
                // Request permission and get token
                const token = await this.firebase.requestPermissionAndGetToken();
                if (token) {
                    // Register with backend
                    await this.backend.register(token);
                    
                    // Setup message listener
                    this.firebase.onMessage((payload) => {
                        console.log('Message received in foreground:', payload);
                        this.notificationUI.show(payload);
                    });
                }
                
                this.setupEventListeners();
            }

            setupEventListeners() {
                // Handle page visibility change
                document.addEventListener('visibilitychange', () => {
                    if (!document.hidden) {
                        const token = this.firebase.getToken();
                        if (token) {
                            this.backend.register(token);
                        }
                    }
                });
            }
        }

        // ================================
        // Application Bootstrap
        // ================================
        document.addEventListener('DOMContentLoaded', () => {
            const app = new FCMApp();
            app.initialize();
        });