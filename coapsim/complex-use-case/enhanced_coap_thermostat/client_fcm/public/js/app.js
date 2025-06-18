// ================================
        // Collapsible Cards Functionality
        // ================================
        function toggleCard(cardId) {
            const card = document.querySelector(`[data-card="${cardId}"]`);
            if (!card) return;
            
            card.classList.toggle('collapsed');
            
            // Save state to localStorage
            const isCollapsed = card.classList.contains('collapsed');
            localStorage.setItem(`card_${cardId}_collapsed`, isCollapsed);
        }

        function initializeCardStates() {
            // Initialize all cards based on saved states
            const cards = document.querySelectorAll('.collapsible-card');
            cards.forEach(card => {
                const cardId = card.getAttribute('data-card');
                const isCollapsed = localStorage.getItem(`card_${cardId}_collapsed`) === 'true';
                
                if (isCollapsed) {
                    card.classList.add('collapsed');
                }
            });
        }

        // Initialize card states when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            initializeCardStates();
        });

        // Global function for removing history items
        window.toggleCard = toggleCard;

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
                    backendUrl: window.env?.BACKEND_URL || "http://localhost:8000",
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
                    notificationContainer: document.getElementById('notificationContainer'),
                    notificationHistory: document.getElementById('notificationHistory'),
                    clearHistoryBtn: document.getElementById('clearHistoryBtn'),
                    connectionControls: document.getElementById('connectionControls'),
                    connectBtn: document.getElementById('connectBtn'),
                    disconnectBtn: document.getElementById('disconnectBtn'),
                    profileRequiredIndicator: document.getElementById('profileRequiredIndicator')
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
        // Notification History Manager
        // ================================
        class NotificationHistoryManager {
            constructor(domManager) {
                this.dom = domManager;
                this.history = this.loadHistory();
                this.setupEventListeners();
                this.renderHistory();
            }

            setupEventListeners() {
                const clearBtn = this.dom.get('clearHistoryBtn');
                if (clearBtn) {
                    clearBtn.addEventListener('click', () => {
                        this.clearHistory();
                    });
                }
            }

            addNotification(payload) {
                const notification = payload.notification || {};
                const data = payload.data || {};
                
                const historyItem = {
                    id: Date.now() + Math.random(),
                    title: notification.title || 'Notification',
                    body: notification.body || 'No message content',
                    timestamp: new Date().toISOString(),
                    data: data
                };

                this.history.unshift(historyItem); // Add to beginning
                
                // Keep only last 50 notifications
                if (this.history.length > 50) {
                    this.history = this.history.slice(0, 50);
                }
                
                this.saveHistory();
                this.renderHistory();
            }

            clearHistory() {
                if (confirm('Are you sure you want to clear all notification history?')) {
                    this.history = [];
                    this.saveHistory();
                    this.renderHistory();
                }
            }

            renderHistory() {
                const container = this.dom.get('notificationHistory');
                if (!container) return;

                if (this.history.length === 0) {
                    container.innerHTML = `
                        <div class="text-white/50 text-sm text-center py-4">
                            No notifications received yet
                        </div>
                    `;
                    return;
                }

                const historyHTML = this.history.map(item => `
                    <div class="history-item rounded-lg p-3 backdrop-blur-sm">
                        <div class="flex items-start justify-between">
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center space-x-2 mb-1">
                                    <h4 class="text-white font-medium text-sm truncate">${this.escapeHtml(item.title)}</h4>
                                    <span class="text-white/50 text-xs flex-shrink-0">${this.formatTime(item.timestamp)}</span>
                                </div>
                                <p class="text-white/70 text-sm">${this.escapeHtml(item.body)}</p>
                                ${item.data.url ? `<a href="${this.escapeHtml(item.data.url)}" class="text-blue-300 text-xs mt-1 block hover:underline" target="_blank">View Details</a>` : ''}
                            </div>
                            <button 
                                class="text-white/40 hover:text-white/70 ml-2 p-1" 
                                onclick="window.notificationHistory.removeItem('${item.id}')"
                                title="Remove this notification"
                            >
                                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                `).join('');

                container.innerHTML = historyHTML;
            }

            removeItem(id) {
                this.history = this.history.filter(item => item.id.toString() !== id.toString());
                this.saveHistory();
                this.renderHistory();
            }

            formatTime(timestamp) {
                const date = new Date(timestamp);
                const now = new Date();
                const diffInMinutes = Math.floor((now - date) / (1000 * 60));
                
                if (diffInMinutes < 1) return 'Just now';
                if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
                if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
                
                return date.toLocaleDateString();
            }

            escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            loadHistory() {
                try {
                    const stored = localStorage.getItem('fcm_notification_history');
                    return stored ? JSON.parse(stored) : [];
                } catch (error) {
                    console.warn('Failed to load notification history:', error);
                    return [];
                }
            }

            saveHistory() {
                try {
                    localStorage.setItem('fcm_notification_history', JSON.stringify(this.history));
                } catch (error) {
                    console.warn('Failed to save notification history:', error);
                }
            }

            getHistory() {
                return this.history;
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
                    case 'connecting':
                        indicator.className += 'bg-blue-400 animate-pulse';
                        break;
                    default:
                        indicator.className += 'bg-gray-400';
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
        // User Profile Manager
        // ================================
        class UserProfileManager {
            constructor(domManager) {
                this.dom = domManager;
                this.userId = this.generateUserId();
                this.username = this.loadUsername();
                this.email = this.loadEmail();
                this.profileSaved = this.isProfileComplete();
                this.setupElements();
                this.setupEventListeners();
                this.initializeDefaultValues();
            }

            setupElements() {
                // Add user profile elements to DOM manager
                this.dom.elements.username = document.getElementById('username');
                this.dom.elements.userEmail = document.getElementById('userEmail');
                this.dom.elements.userId = document.getElementById('userId');
                this.dom.elements.updateProfileBtn = document.getElementById('updateProfileBtn');
                this.dom.elements.clearProfileBtn = document.getElementById('clearProfileBtn');
                this.dom.elements.profileStatus = document.getElementById('profileStatus');
                
                // Check if elements exist before setting values
                if (this.dom.elements.userId) {
                    this.dom.elements.userId.value = this.userId;
                }
                if (this.dom.elements.username) {
                    this.dom.elements.username.value = this.username;
                }
                if (this.dom.elements.userEmail) {
                    this.dom.elements.userEmail.value = this.email;
                }
            }

            initializeDefaultValues() {
                // Update profile indicator based on current state
                this.updateProfileIndicator();
                
                // If no username is stored, prompt user to enter one
                if (!this.username && this.dom.elements.username) {
                    this.dom.elements.username.placeholder = "Please enter your name to continue";
                    this.dom.elements.username.focus();
                }
            }

            updateProfileIndicator() {
                const indicator = this.dom.get('profileRequiredIndicator');
                if (indicator) {
                    if (this.profileSaved) {
                        indicator.textContent = '(Profile Complete)';
                        indicator.className = 'ml-2 text-green-300 text-sm';
                    } else {
                        indicator.textContent = '(Required to connect)';
                        indicator.className = 'ml-2 text-red-300 text-sm';
                    }
                }
            }

            setupEventListeners() {
                // Update profile button
                if (this.dom.elements.updateProfileBtn) {
                    this.dom.elements.updateProfileBtn.addEventListener('click', () => {
                        this.updateProfile();
                    });
                }

                // Clear profile button
                if (this.dom.elements.clearProfileBtn) {
                    this.dom.elements.clearProfileBtn.addEventListener('click', () => {
                        this.clearProfile();
                    });
                }

                // Auto-save on blur (optional - you can remove this if you prefer manual save only)
                if (this.dom.elements.username) {
                    this.dom.elements.username.addEventListener('input', () => {
                        this.validateUsername();
                    });
                }

                if (this.dom.elements.userEmail) {
                    this.dom.elements.userEmail.addEventListener('input', () => {
                        this.validateEmail();
                    });
                }

                // Enter key to save
                if (this.dom.elements.username) {
                    this.dom.elements.username.addEventListener('keypress', (e) => {
                        if (e.key === 'Enter') {
                            this.updateProfile();
                        }
                    });
                }

                if (this.dom.elements.userEmail) {
                    this.dom.elements.userEmail.addEventListener('keypress', (e) => {
                        if (e.key === 'Enter') {
                            this.updateProfile();
                        }
                    });
                }
            }

            validateUsername() {
                const username = this.dom.elements.username?.value.trim();
                const isValid = username && username.length >= 2 && username.length <= 30;
                
                if (this.dom.elements.username) {
                    this.dom.elements.username.style.borderColor = isValid ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)';
                }
                
                return isValid;
            }

            validateEmail() {
                const email = this.dom.elements.userEmail?.value.trim();
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                const isValid = !email || emailRegex.test(email); // Empty email is valid (optional field)
                
                if (this.dom.elements.userEmail) {
                    this.dom.elements.userEmail.style.borderColor = isValid ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)';
                }
                
                return isValid;
            }

            updateProfile() {
                const newUsername = this.dom.elements.username?.value.trim() || '';
                const newEmail = this.dom.elements.userEmail?.value.trim() || '';
                
                // Validate inputs
                if (!newUsername) {
                    this.showProfileMessage('Please enter a username', 'error');
                    this.dom.elements.username?.focus();
                    return;
                }

                if (newUsername.length < 2) {
                    this.showProfileMessage('Username must be at least 2 characters', 'error');
                    this.dom.elements.username?.focus();
                    return;
                }

                if (newEmail && !this.validateEmail()) {
                    this.showProfileMessage('Please enter a valid email address', 'error');
                    this.dom.elements.userEmail?.focus();
                    return;
                }

                // Save the values
                this.username = newUsername;
                this.email = newEmail;
                this.saveUsername(this.username);
                this.saveEmail(this.email);
                this.profileSaved = true;

                // Show success message
                this.showProfileMessage('Profile updated successfully!', 'success');
                
                // Reset border colors
                if (this.dom.elements.username) {
                    this.dom.elements.username.style.borderColor = '';
                }
                if (this.dom.elements.userEmail) {
                    this.dom.elements.userEmail.style.borderColor = '';
                }

                // Update profile indicator and show connection controls
                this.updateProfileIndicator();
                this.showConnectionControls();

                console.log('✅ Profile updated:', { username: this.username, email: this.email, userId: this.userId });

                // Trigger connection process if this is the save & connect button
                if (window.fcmApp && typeof window.fcmApp.initiateConnection === 'function') {
                    setTimeout(() => {
                        window.fcmApp.initiateConnection();
                    }, 1000);
                }
            }

            clearProfile() {
                if (confirm('Are you sure you want to clear all profile data? This will reset your username and email.')) {
                    // Clear the form fields
                    if (this.dom.elements.username) {
                        this.dom.elements.username.value = '';
                    }
                    if (this.dom.elements.userEmail) {
                        this.dom.elements.userEmail.value = '';
                    }

                    // Clear stored data
                    this.username = '';
                    this.email = '';
                    this.profileSaved = false;
                    localStorage.removeItem('fcm_username');
                    localStorage.removeItem('fcm_email');

                    // Reset border colors
                    if (this.dom.elements.username) {
                        this.dom.elements.username.style.borderColor = '';
                    }
                    if (this.dom.elements.userEmail) {
                        this.dom.elements.userEmail.style.borderColor = '';
                    }

                    this.showProfileMessage('Profile cleared', 'success');
                    this.updateProfileIndicator();
                    this.hideConnectionControls();
                    
                    // Focus on username field
                    setTimeout(() => {
                        this.dom.elements.username?.focus();
                    }, 100);
                }
            }

            showConnectionControls() {
                const controls = this.dom.get('connectionControls');
                if (controls) {
                    controls.classList.remove('hidden');
                }
            }

            hideConnectionControls() {
                const controls = this.dom.get('connectionControls');
                if (controls) {
                    controls.classList.add('hidden');
                }
            }

            showProfileMessage(message, type = 'success') {
                if (this.dom.elements.profileStatus) {
                    this.dom.elements.profileStatus.textContent = message;
                    this.dom.elements.profileStatus.className = `text-center text-sm ${
                        type === 'error' ? 'text-red-300' : 'text-green-300'
                    }`;
                    this.dom.elements.profileStatus.classList.remove('hidden');

                    // Hide after 3 seconds
                    setTimeout(() => {
                        this.dom.elements.profileStatus.classList.add('hidden');
                    }, 3000);
                }

                // Also update the update button temporarily
                if (this.dom.elements.updateProfileBtn) {
                    const originalText = this.dom.elements.updateProfileBtn.textContent;
                    const icon = type === 'error' ? '❌' : '✅';
                    this.dom.elements.updateProfileBtn.textContent = `${icon} ${message}`;
                    
                    if (type === 'success') {
                        this.dom.elements.updateProfileBtn.classList.add('bg-green-500/30', 'text-green-200');
                    } else {
                        this.dom.elements.updateProfileBtn.classList.add('bg-red-500/30', 'text-red-200');
                    }
                    
                    setTimeout(() => {
                        this.dom.elements.updateProfileBtn.textContent = originalText;
                        this.dom.elements.updateProfileBtn.classList.remove('bg-green-500/30', 'text-green-200', 'bg-red-500/30', 'text-red-200');
                    }, 2000);
                }
            }

            generateUserId() {
                // Check if user ID already exists in localStorage
                const existingId = localStorage.getItem('fcm_user_id');
                if (existingId) {
                    return existingId;
                }
                
                // Generate a unique user ID
                const timestamp = Date.now();
                const random = Math.floor(Math.random() * 1000);
                const newId = `user_${timestamp}_${random}`;
                
                // Save to localStorage
                localStorage.setItem('fcm_user_id', newId);
                return newId;
            }

            loadUsername() {
                return localStorage.getItem('fcm_username') || '';
            }

            saveUsername(username) {
                localStorage.setItem('fcm_username', username);
                this.username = username;
            }

            loadEmail() {
                return localStorage.getItem('fcm_email') || '';
            }

            saveEmail(email) {
                localStorage.setItem('fcm_email', email);
                this.email = email;
            }

            isProfileComplete() {
                return !!(this.username && this.username.length >= 2);
            }

            getUserInfo() {
                return {
                    userId: this.userId,
                    username: this.username || 'Anonymous',
                    email: this.email || ''
                };
            }

            isProfileSectionAvailable() {
                return !!(document.getElementById('username') && 
                         document.getElementById('userEmail') && 
                         document.getElementById('userId'));
            }
        }

        // ================================
        // Notification UI Manager
        // ================================
        class NotificationUIManager {
            constructor(domManager, statsManager, historyManager) {
                this.dom = domManager;
                this.stats = statsManager;
                this.history = historyManager;
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
                this.history.addNotification(payload);
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

            async deleteToken() {
                if (this.messaging && this.token) {
                    try {
                        // Firebase doesn't have a direct deleteToken method in v9
                        // Instead, we can request a new token which effectively invalidates the old one
                        await window.firebaseMessaging.getToken(this.messaging, {
                            vapidKey: this.config.get('vapidKey')
                        });
                        console.log('FCM token refreshed (old token invalidated)');
                        return true;
                    } catch (error) {
                        console.error('Failed to refresh FCM token:', error);
                        throw error;
                    }
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
            constructor(config, statusManager, userProfileManager) {
                this.config = config;
                this.status = statusManager;
                this.userProfile = userProfileManager;
            }

            async register(token) {
                try {
                    console.log('Registering with backend...');
                    console.log('Backend URL:', this.config.get('backendUrl'));
                    
                    const userInfo = this.userProfile.getUserInfo();
                    
                    // Add more explicit headers for CORS
                    const response = await fetch(`${this.config.get('backendUrl')}/register`, {
                        method: 'POST',
                        mode: 'cors', // Explicitly set CORS mode
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                        },
                        body: JSON.stringify({
                            token: token,
                            platform: 'web',
                            userAgent: navigator.userAgent,
                            timestamp: new Date().toISOString(),
                            userId: userInfo.userId,
                            username: userInfo.username,
                            email: userInfo.email
                        })
                    });

                    // Log the response for debugging
                    console.log('Response status:', response.status);
                    console.log('Response headers:', response.headers);

                    if (response.ok) {
                        const result = await response.json();
                        console.log('Registration successful:', result);
                        this.status.update('success', 'Connected and ready');
                        this.status.updateRegistrationStatus(`Successfully registered as ${userInfo.username}`);
                        return true;
                    } else {
                        const errorText = await response.text();
                        throw new Error(`Registration failed: ${response.status} - ${errorText}`);
                    }
                } catch (error) {
                    console.error('Backend registration error:', error);
                    
                    // More specific error handling
                    if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                        this.status.update('error', 'Cannot connect to backend server');
                        this.status.updateRegistrationStatus('Error: Backend server unreachable. Check if backend is running on ' + this.config.get('backendUrl'));
                    } else {
                        this.status.update('warning', 'Ready (backend registration failed)');
                        this.status.updateRegistrationStatus('Warning: Backend registration failed - ' + error.message);
                    }
                    return false;
                }
            }

            async unregister(token) {
                try {
                    console.log('Unregistering from backend...');
                    console.log('Backend URL:', this.config.get('backendUrl'));
                    
                    const userInfo = this.userProfile.getUserInfo();
                    
                    const response = await fetch(`${this.config.get('backendUrl')}/unregister`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            token: token,
                            userId: userInfo.userId,
                            timestamp: new Date().toISOString()
                        })
                    });

                    if (response.ok) {
                        const result = await response.json();
                        console.log('Unregistration successful:', result);
                        return true;
                    } else {
                        // Don't throw error for 404 - token might already be removed
                        if (response.status === 404) {
                            console.log('Token not found on server (already removed)');
                            return true;
                        }
                        throw new Error(`Unregistration failed: ${response.status}`);
                    }
                } catch (error) {
                    console.error('Backend unregistration error:', error);
                    // For disconnect, we don't want to fail the entire process
                    // if backend is unavailable
                    if (error.name === 'TypeError' && error.message.includes('fetch')) {
                        console.log('Backend unavailable during disconnect - proceeding with local disconnect');
                        return true;
                    }
                    throw error;
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
                if (durationSlider) {
                    durationSlider.addEventListener('input', (e) => {
                        const value = parseInt(e.target.value);
                        const duration = value * 1000;
                        this.notificationUI.setDuration(duration);
                        this.dom.updateText('durationValue', value + 's');
                    });
                }
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
                console.log(this.config.config)
                this.dom = new DOMManager();
                this.status = new StatusManager(this.dom);
                this.stats = new StatsManager(this.dom);
                this.history = new NotificationHistoryManager(this.dom);
                
                // Initialize user profile manager with fallback
                try {
                    this.userProfile = new UserProfileManager(this.dom);
                } catch (error) {
                    console.warn('User profile section not available, using fallback');
                    this.userProfile = this.createFallbackUserProfile();
                }
                
                this.notificationUI = new NotificationUIManager(this.dom, this.stats, this.history);
                this.firebase = new FirebaseManager(this.config, this.status);
                this.backend = new BackendService(this.config, this.status, this.userProfile);
                this.settings = new SettingsManager(this.dom, this.notificationUI);
                this.serviceWorker = new ServiceWorkerManager();
                
                this.isConnected = false;
                
                // Expose app instance globally for profile manager access
                window.fcmApp = this;
                
                // Expose history for global access
                window.notificationHistory = this.history;
            }

            // Fallback user profile for when profile elements don't exist
            createFallbackUserProfile() {
                return {
                    userId: this.generateFallbackUserId(),
                    username: localStorage.getItem('fcm_username') || 'Anonymous',
                    email: localStorage.getItem('fcm_email') || '',
                    profileSaved: true,
                    
                    getUserInfo() {
                        return {
                            userId: this.userId,
                            username: this.username,
                            email: this.email
                        };
                    },
                    
                    isProfileSectionAvailable() {
                        return false;
                    }
                };
            }

            generateFallbackUserId() {
                const existingId = localStorage.getItem('fcm_user_id');
                if (existingId) {
                    return existingId;
                }
                
                const timestamp = Date.now();
                const random = Math.floor(Math.random() * 1000);
                const newId = `user_${timestamp}_${random}`;
                localStorage.setItem('fcm_user_id', newId);
                return newId;
            }

            async initialize() {
                console.log('App initializing...');
                this.status.update('loading', 'Initializing...');
                
                if (this.config.isDevelopment()) {
                    console.log('Development mode detected');
                }
                
                // Register service worker
                await this.serviceWorker.register();
                
                // Check if profile is complete
                if (!this.userProfile.profileSaved) {
                    this.status.update('warning', 'Profile setup required');
                    this.status.updateTokenStatus('Please complete your profile first');
                    this.status.updateRegistrationStatus('Save your profile to enable connection');
                    return;
                }
                
                // If profile is complete, show connection controls
                this.userProfile.showConnectionControls?.();
                
                this.setupEventListeners();
            }

            async initiateConnection() {
                if (this.isConnected) {
                    console.log('Already connected');
                    return;
                }

                console.log('Initiating connection...');
                this.status.update('connecting', 'Connecting...');
                this.status.updateTokenStatus('Requesting FCM token...');
                this.status.updateRegistrationStatus('Initializing Firebase...');
                
                // Initialize Firebase
                const firebaseInitialized = await this.firebase.initialize();
                if (!firebaseInitialized) {
                    return;
                }
                
                // Request permission and get token
                const token = await this.firebase.requestPermissionAndGetToken();
                if (token) {
                    // Register with backend
                    const registered = await this.backend.register(token);
                    if (registered) {
                        // Setup message listener
                        this.firebase.onMessage((payload) => {
                            console.log('Message received in foreground:', payload);
                            this.notificationUI.show(payload);
                        });
                        
                        this.isConnected = true;
                        this.updateConnectionButtons();
                    }
                }
            }

            async disconnect() {
                if (!this.isConnected) {
                    console.log('Already disconnected');
                    return;
                }

                console.log('Disconnecting from FCM service...');
                this.status.update('connecting', 'Disconnecting...');
                this.status.updateTokenStatus('Removing registration...');
                this.status.updateRegistrationStatus('Disconnecting from server...');

                try {
                    // 1. Notify backend to remove this client
                    const token = this.firebase.getToken();
                    if (token) {
                        await this.backend.unregister(token);
                    }

                    // 2. Delete the FCM token to prevent further notifications
                    if (this.messaging) {
                        try {
                            await this.firebase.deleteToken();
                        } catch (error) {
                            console.warn('Failed to delete FCM token:', error);
                        }
                    }

                    // 3. Clear local token storage
                    this.firebase.token = null;

                    // 4. Update UI state
                    this.isConnected = false;
                    this.status.update('warning', 'Disconnected');
                    this.status.updateTokenStatus('Token removed - no longer receiving notifications');
                    this.status.updateRegistrationStatus('Successfully disconnected from server');
                    this.updateConnectionButtons();
                    
                    console.log('✅ Successfully disconnected from FCM service');

                } catch (error) {
                    console.error('Error during disconnection:', error);
                    // Still mark as disconnected locally even if backend call failed
                    this.isConnected = false;
                    this.status.update('error', 'Disconnect error (marked as disconnected)');
                    this.status.updateTokenStatus('Disconnect error, but marked as disconnected locally');
                    this.status.updateRegistrationStatus('Error: ' + error.message);
                    this.updateConnectionButtons();
                }
            }

            updateConnectionButtons() {
                const connectBtn = this.dom.get('connectBtn');
                const disconnectBtn = this.dom.get('disconnectBtn');
                
                if (connectBtn && disconnectBtn) {
                    if (this.isConnected) {
                        connectBtn.classList.add('hidden');
                        disconnectBtn.classList.remove('hidden');
                    } else {
                        connectBtn.classList.remove('hidden');
                        disconnectBtn.classList.add('hidden');
                    }
                }
            }

            setupEventListeners() {
                // Connect button
                const connectBtn = this.dom.get('connectBtn');
                if (connectBtn) {
                    connectBtn.addEventListener('click', () => {
                        this.initiateConnection();
                    });
                }
                
                // Disconnect button
                const disconnectBtn = this.dom.get('disconnectBtn');
                if (disconnectBtn) {
                    disconnectBtn.addEventListener('click', () => {
                        this.disconnect();
                    });
                }
                
                // Handle page visibility change
                document.addEventListener('visibilitychange', () => {
                    if (!document.hidden && this.isConnected) {
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