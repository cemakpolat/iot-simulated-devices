class ApiService {
    constructor() {
        this.baseUrl = '';
    }

    async request(endpoint, options = {}) {
        const response = await fetch(this.baseUrl + endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    async getStats() {
        return this.request('/api/stats');
    }

    async getDevices() {
        return this.request('/api/devices');
    }

    async getUnknownDevices() {
        return this.request('/api/discovery/unknown');
    }

    async getMetrics() {
        return this.request('/monitoring/metrics/json');
    }

    async getHealth(detailed = false) {
        const param = detailed ? '?detailed=true' : '';
        return this.request(`/monitoring/health${param}`);
    }

    async getPerformance() {
        return this.request('/monitoring/performance');
    }

    async getAlerts() {
        return this.request('/monitoring/alerts');
    }

    async simulatePacket(deviceId, packetData) {
        return this.request('/api/test/packet', {
            method: 'POST',
            body: JSON.stringify({ device_id: deviceId, packet_data: packetData })
        });
    }

    async simulateUnknownDevice(rorg) {
        const rorgMap = { 'A5': 0xA5, 'F6': 0xF6, 'D5': 0xD5, 'D2': 0xD2 };
        return this.request('/api/test/unknown_device', {
            method: 'POST',
            body: JSON.stringify({ rorg: rorgMap[rorg], packet_count: 5 })
        });
    }

    async testDevice(deviceId) {
        return this.request(`/api/test/device/${deviceId}`, {
            method: 'POST'
        });
    }

    async addDevice(deviceData) {
        return this.request('/api/devices', {
            method: 'POST',
            body: JSON.stringify(deviceData)
        });
    }

    async removeDevice(deviceId) {
        return this.request(`/api/devices/${deviceId}`, {
            method: 'DELETE'
        });
    }

    async registerDevice(deviceData) {
        return this.request('/api/devices/register', {
            method: 'POST',
            body: JSON.stringify(deviceData)
        });
    }

    async ignoreDevice(deviceId) {
        return this.request(`/api/devices/${deviceId}/ignore`, {
            method: 'POST'
        });
    }

    // System operations
    async refreshSystem() {
        return this.request('/api/system/refresh', {
            method: 'POST'
        });
    }
}

function dashboardApp() {
    return {
        // State
        activeTab: 'devices',
        isLoading: false,
        devices: [],
        unknownDevices: [],
        metrics: [],
        healthChecks: [],
        performanceMetrics: [],
        alerts: [],
        notifications: [],
        newDevice: {
            device_id: '',
            name: '',
            eep_profile: '',
            location: '',
            manufacturer: '',
            model: '',
            description: ''
        },
        testPacket: {
            device_id: '',
            packet_data: ''
        },

        // Optimized stats - single source from /api/stats
        stats: [
            { id: 'devices', label: 'Registered Devices', value: '0', trend: 0, icon: 'fas fa-microchip', iconBg: 'bg-blue-600' },
            { id: 'active', label: 'Active Devices', value: '0', trend: 0, icon: 'fas fa-wifi', iconBg: 'bg-green-600' },
            { id: 'unknown', label: 'Unknown Devices', value: '0', trend: 0, icon: 'fas fa-question-circle', iconBg: 'bg-orange-600' },
            { id: 'packets', label: 'Packets Processed', value: '0', trend: 0, icon: 'fas fa-exchange-alt', iconBg: 'bg-purple-600' }
        ],

        tabs: [
            { id: 'devices', name: 'Devices', icon: 'fas fa-microchip' },
            { id: 'discovery', name: 'Discovery', icon: 'fas fa-search', badge: 0 },
            { id: 'monitoring', name: 'Monitoring', icon: 'fas fa-chart-line' },
            { id: 'health', name: 'Health', icon: 'fas fa-heartbeat' },
            { id: 'performance', name: 'Performance', icon: 'fas fa-tachometer-alt' },
            { id: 'add-device', name: 'Add Device', icon: 'fas fa-plus' },
            { id: 'testing', name: 'Testing', icon: 'fas fa-flask' }
        ],

        // Services
        apiService: null,

        // Initialization
        init() {
            this.apiService = new ApiService();
            this.loadAllData();
            this.setupAutoRefresh();
            this.trackPerformance();
        },

        setupAutoRefresh() {
            // Optimized: Staggered refresh intervals
            setInterval(() => this.loadStats(), 15000);           // Every 15s
            setInterval(() => this.loadDevices(), 30000);         // Every 30s  
            setInterval(() => this.loadUnknownDevices(), 45000);  // Every 45s
            setInterval(() => this.loadMonitoringData(), 30000);  // Every 30s
            setInterval(() => this.loadHealthData(), 60000);      // Every 60s
        },

        async loadAllData() {
            this.isLoading = true;
            try {
                // Parallel loading of all data
                const [stats, devices, unknown, monitoring, health, performance] = await Promise.allSettled([
                    this.apiService.getStats(),
                    this.apiService.getDevices(),
                    this.apiService.getUnknownDevices(),
                    this.apiService.getMetrics(),
                    this.apiService.getHealth(true), // Get detailed health
                    this.apiService.getPerformance()
                ]);

                // Process results
                if (stats.status === 'fulfilled') this.updateStatsDisplay(stats.value);
                if (devices.status === 'fulfilled') this.devices = devices.value.devices || [];
                if (unknown.status === 'fulfilled') {
                    this.unknownDevices = unknown.value.unknown_devices || [];
                    this.updateDiscoveryBadge();
                }
                if (monitoring.status === 'fulfilled') this.processMetricsData(monitoring.value);
                if (health.status === 'fulfilled') this.processHealthData(health.value);
                if (performance.status === 'fulfilled') this.processPerformanceData(performance.value);

            } catch (error) {
                this.showNotification('error', 'Loading Error', 'Failed to load some data');
                console.error('Error loading data:', error);
            } finally {
                this.isLoading = false;
            }
        },

        async loadStats() {
            try {
                const stats = await this.apiService.getStats();
                this.updateStatsDisplay(stats);
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        },

        async loadDevices() {
            try {
                const response = await this.apiService.getDevices();
                this.devices = response.devices || [];
            } catch (error) {
                console.error('Error loading devices:', error);
            }
        },

        async loadUnknownDevices() {
            try {
                const response = await this.apiService.getUnknownDevices();
                this.unknownDevices = response.unknown_devices || [];
                this.updateDiscoveryBadge();
            } catch (error) {
                console.error('Error loading unknown devices:', error);
            }
        },

        async loadMonitoringData() {
            try {
                const [metricsData, alertsData] = await Promise.allSettled([
                    this.apiService.getMetrics(),
                    this.apiService.getAlerts()
                ]);

                if (metricsData.status === 'fulfilled') {
                    this.processMetricsData(metricsData.value);
                }
                if (alertsData.status === 'fulfilled') {
                    this.alerts = alertsData.value.alerts || [];
                }
            } catch (error) {
                console.warn('Monitoring data not available:', error);
            }
        },

        async loadHealthData() {
            try {
                const healthData = await this.apiService.getHealth(true);
                this.processHealthData(healthData);
            } catch (error) {
                console.warn('Health data not available:', error);
            }
        },

        async loadPerformanceData() {
            try {
                const perfData = await this.apiService.getPerformance();
                this.processPerformanceData(perfData);
            } catch (error) {
                console.warn('Performance data not available:', error);
            }
        },

        updateStatsDisplay(stats) {
            // Direct mapping from optimized API response
            this.stats[0].value = (stats.total_devices || 0).toString();
            this.stats[1].value = (stats.active_devices || 0).toString(); 
            this.stats[2].value = (stats.unknown_devices_detected || 0).toString();
            this.stats[3].value = (stats.total_packets_processed || 0).toString();
        },

        processMetricsData(metricsData) {
            if (!metricsData.success) {
                this.metrics = [];
                return;
            }

            this.metrics = [];

            // Process counters and gauges together
            ['counters', 'gauges'].forEach(type => {
                if (metricsData[type]) {
                    Object.entries(metricsData[type]).forEach(([name, data]) => {
                        this.metrics.push({
                            name: name,
                            value: data.value || 0,
                            description: data.description || `${type.slice(0, -1)} metric`,
                            type: type.slice(0, -1) // Remove 's'
                        });
                    });
                }
            });
        },

        processHealthData(healthData) {
            this.healthChecks = [];
            
            if (healthData.checks) {
                Object.entries(healthData.checks).forEach(([name, check]) => {
                    this.healthChecks.push({
                        name: name,
                        status: check.status || 'unknown',
                        last_check: check.last_check,
                        error: check.error,
                        message: check.message
                    });
                });
            }
        },

        processPerformanceData(perfData) {
            if (perfData.system) {
                this.performanceMetrics = [
                    {
                        name: 'CPU Usage',
                        value: Math.round(perfData.system.cpu_percent || 0),
                        description: 'Current CPU utilization'
                    },
                    {
                        name: 'Memory Usage', 
                        value: Math.round(perfData.system.memory_percent || 0),
                        description: 'RAM consumption'
                    },
                    {
                        name: 'Disk Usage',
                        value: Math.round(perfData.system.disk_percent || 0),
                        description: 'Storage utilization'
                    }
                ];
            }
        },

        updateDiscoveryBadge() {
            const discoveryTab = this.tabs.find(tab => tab.id === 'discovery');
            if (discoveryTab) {
                discoveryTab.badge = this.unknownDevices.length;
            }
        },

        async submitDevice() {
            try {
                const response = await this.apiService.addDevice(this.newDevice);
                if (response.success) {
                    this.showNotification('success', 'Device Added', `${this.newDevice.name} was registered successfully`);
                    this.clearForm();
                    // Optimized: Only reload necessary data
                    await Promise.all([this.loadDevices(), this.loadStats()]);
                } else {
                    this.showNotification('error', 'Add Failed', response.error || 'Unknown error');
                }
            } catch (error) {
                this.showNotification('error', 'Add Failed', error.message);
            }
        },

        async removeDevice(deviceId) {
            if (!confirm(`Are you sure you want to remove device ${deviceId}?`)) return;

            try {
                const response = await this.apiService.removeDevice(deviceId);
                if (response.success) {
                    this.showNotification('success', 'Device Removed', 'Device was successfully removed');
                    await Promise.all([this.loadDevices(), this.loadStats()]);
                } else {
                    this.showNotification('error', 'Remove Failed', response.error || 'Unknown error');
                }
            } catch (error) {
                this.showNotification('error', 'Remove Failed', error.message);
            }
        },

        async registerFromSuggestion(deviceId, eepProfile) {
            const name = prompt(`Enter a name for device ${deviceId}:`);
            if (!name) return;

            const location = prompt('Enter location (optional):') || '';

            try {
                const response = await this.apiService.registerDevice({
                    device_id: deviceId,
                    name: name,
                    eep_profile: eepProfile,
                    location: location
                });
                
                if (response.success) {
                    this.showNotification('success', 'Device Registered', `${name} was registered successfully`);
                    await Promise.all([this.loadDevices(), this.loadUnknownDevices(), this.loadStats()]);
                } else {
                    this.showNotification('error', 'Registration Failed', response.error || 'Unknown error');
                }
            } catch (error) {
                this.showNotification('error', 'Registration Failed', error.message);
            }
        },

        async ignoreDevice(deviceId) {
            try {
                const response = await this.apiService.ignoreDevice(deviceId);
                if (response.success) {
                    this.showNotification('info', 'Device Ignored', 'Device will no longer appear in discovery');
                    await this.loadUnknownDevices();
                } else {
                    this.showNotification('error', 'Ignore Failed', response.error || 'Unknown error');
                }
            } catch (error) {
                this.showNotification('error', 'Ignore Failed', error.message);
            }
        },

        async simulateUnknownDevice(rorgType) {
            try {
                const result = await this.apiService.simulateUnknownDevice(rorgType);
                if (result.success) {
                    this.showNotification('success', 'Device Simulated', `Generated unknown ${rorgType} device`);
                    await this.loadStats();
                    if (this.activeTab === 'discovery') {
                        setTimeout(() => this.loadUnknownDevices(), 1000);
                    }
                } else {
                    this.showNotification('error', 'Simulation Failed', result.error || 'Unknown error');
                }
            } catch (error) {
                this.showNotification('error', 'Simulation Failed', error.message);
            }
        },

        async simulatePacket() {
            if (!this.testPacket.device_id || !this.testPacket.packet_data) {
                this.showNotification('error', 'Missing Data', 'Please enter both device ID and packet data');
                return;
            }

            try {
                const response = await this.apiService.simulatePacket(this.testPacket.device_id, this.testPacket.packet_data);
                if (response.success) {
                    this.showNotification('success', 'Packet Sent', `Packet sent to ${this.testPacket.device_id}`);
                    await this.loadStats();
                } else {
                    this.showNotification('error', 'Packet Failed', response.error || 'Unknown error');
                }
            } catch (error) {
                this.showNotification('error', 'Packet Failed', error.message);
            }
        },

        testDevice(deviceId) {
            this.testPacket.device_id = deviceId;
            this.activeTab = 'testing';
            this.showNotification('info', 'Test Mode', `Ready to test device ${deviceId}`);
        },

        async quickTestDevice(deviceId) {
            try {
                const response = await this.apiService.testDevice(deviceId);
                if (response.success) {
                    this.showNotification('success', 'Test Sent', `Test packet sent to device ${deviceId}`);
                    await this.loadStats();
                } else {
                    this.showNotification('error', 'Test Failed', response.error || 'Unknown error');
                }
            } catch (error) {
                this.showNotification('error', 'Test Failed', error.message);
            }
        },

        async refreshDevices() {
            this.isLoading = true;
            await this.loadDevices();
            this.isLoading = false;
            this.showNotification('success', 'Refreshed', 'Device list updated');
        },

        async refreshUnknownDevices() {
            this.isLoading = true;
            await this.loadUnknownDevices();
            this.isLoading = false;
            this.showNotification('success', 'Scan Complete', 'Unknown devices updated');
        },

        async refreshMetrics() {
            this.isLoading = true;
            await this.loadMonitoringData();
            this.isLoading = false;
            this.showNotification('success', 'Metrics Refreshed', 'Latest data loaded');
        },

        async refreshSystem() {
            this.isLoading = true;
            try {
                await this.apiService.refreshSystem();
                await this.loadAllData();
                this.showNotification('success', 'System Refreshed', 'All data reloaded');
            } catch (error) {
                this.showNotification('error', 'Refresh Failed', error.message);
            } finally {
                this.isLoading = false;
            }
        },

        clearForm() {
            this.newDevice = {
                device_id: '',
                name: '',
                eep_profile: '',
                location: '',
                manufacturer: '',
                model: '',
                description: ''
            };
        },

        editDevice(deviceId) {
            const device = this.devices.find(d => d.device_id === deviceId);
            if (device) {
                this.newDevice = { ...device };
                this.activeTab = 'add-device';
                this.showNotification('info', 'Edit Mode', `Editing device ${device.name}`);
            }
        },

        showRegisterDialog(deviceId) {
            const name = prompt(`Enter a name for device ${deviceId}:`);
            if (!name) return;

            const eepProfile = prompt('Enter EEP profile (e.g., A5-04-01):');
            if (!eepProfile) return;

            this.registerFromSuggestion(deviceId, eepProfile);
        },

        getStatusBadgeClass(status) {
            const classes = {
                'active': 'bg-green-500/20 text-green-400',
                'inactive': 'bg-gray-500/20 text-gray-400', 
                'pending': 'bg-yellow-500/20 text-yellow-400',
                'error': 'bg-red-500/20 text-red-400'
            };
            return classes[status] || classes['inactive'];
        },

        getHealthBadgeClass(status) {
            const classes = {
                'healthy': 'bg-green-500/20 text-green-400',
                'unhealthy': 'bg-red-500/20 text-red-400',
                'unknown': 'bg-gray-500/20 text-gray-400'
            };
            return classes[status] || classes['unknown'];
        },

        getHealthBorderClass(status) {
            const classes = {
                'healthy': 'border-green-500/30',
                'unhealthy': 'border-red-500/30',
                'unknown': 'border-gray-500/30'
            };
            return classes[status] || classes['unknown'];
        },

        getPerformanceColor(value) {
            if (value > 80) return 'text-red-400';
            if (value > 60) return 'text-yellow-400';
            return 'text-green-400';
        },

        getPerformanceBarClass(value) {
            if (value > 80) return 'bg-gradient-to-r from-red-500 to-red-600';
            if (value > 60) return 'bg-gradient-to-r from-yellow-500 to-yellow-600';
            return 'bg-gradient-to-r from-green-500 to-green-600';
        },

        getToastIcon(type) {
            const icons = {
                'success': 'fas fa-check-circle text-green-400',
                'error': 'fas fa-exclamation-circle text-red-400',
                'warning': 'fas fa-exclamation-triangle text-yellow-400',
                'info': 'fas fa-info-circle text-blue-400'
            };
            return icons[type] || icons['info'];
        },

        // Notification Methods (unchanged)
        showNotification(type, title, message) {
            const notification = {
                id: Date.now(),
                type,
                title,
                message,
                show: true
            };

            this.notifications.push(notification);

            setTimeout(() => {
                this.removeNotification(notification.id);
            }, 5000);
        },

        removeNotification(id) {
            const index = this.notifications.findIndex(n => n.id === id);
            if (index > -1) {
                this.notifications[index].show = false;
                setTimeout(() => {
                    this.notifications.splice(index, 1);
                }, 300);
            }
        },

        formatDate(timestamp) {
            if (!timestamp) return 'Never';
            const date = new Date(timestamp * 1000);
            return date.toLocaleString();
        },

        formatTimeAgo(timestamp) {
            if (!timestamp) return 'Never';
            const now = Date.now();
            const diff = now - (timestamp * 1000);
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(minutes / 60);
            const days = Math.floor(hours / 24);

            if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
            if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
            if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
            return 'Just now';
        },

        formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        formatPercentage(value, total) {
            if (total === 0) return '0%';
            return ((value / total) * 100).toFixed(1) + '%';
        },

        trackPerformance() {
            if (typeof performance !== 'undefined' && performance.mark) {
                performance.mark('dashboard-load-start');

                setTimeout(() => {
                    performance.mark('dashboard-load-end');
                    performance.measure('dashboard-load', 'dashboard-load-start', 'dashboard-load-end');

                    const measure = performance.getEntriesByName('dashboard-load')[0];
                    console.log(`Dashboard loaded in ${measure.duration.toFixed(2)}ms`);
                }, 100);
            }
        },

        handleKeyboardShortcuts(event) {
            if (event.ctrlKey || event.metaKey) {
                switch (event.key) {
                    case 'r':
                        event.preventDefault();
                        this.refreshCurrentTab();
                        break;
                    case 'n':
                        event.preventDefault();
                        this.activeTab = 'add-device';
                        break;
                    case 't':
                        event.preventDefault();
                        this.activeTab = 'testing';
                        break;
                }
            }

            if (event.key === 'Escape') {
                this.notifications = [];
            }
        },

        refreshCurrentTab() {
            switch (this.activeTab) {
                case 'devices':
                    this.refreshDevices();
                    break;
                case 'discovery':
                    this.refreshUnknownDevices();
                    break;
                case 'monitoring':
                    this.refreshMetrics();
                    break;
                default:
                    this.refreshSystem();
            }
        },

        exportData() {
            const data = {
                devices: this.devices,
                unknownDevices: this.unknownDevices,
                stats: this.stats,
                timestamp: new Date().toISOString()
            };

            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `enocean_gateway_export_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('success', 'Export Complete', 'Data exported successfully');
        }
    };
}

// Event listeners
document.addEventListener('keydown', function(event) {
    const app = document.querySelector('#app').__x?.$data;
    if (app && typeof app.handleKeyboardShortcuts === 'function') {
        app.handleKeyboardShortcuts(event);
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const app = document.querySelector('#app').__x?.$data;
    if (app && typeof app.trackPerformance === 'function') {
        app.trackPerformance();
    }
});

window.addEventListener('error', function(event) {
    const app = document.querySelector('#app').__x?.$data;
    if (app && typeof app.showNotification === 'function') {
        app.showNotification('error', 'System Error', 'An error occurred');
    }
});

window.addEventListener('unhandledrejection', function(event) {
    const app = document.querySelector('#app').__x?.$data;
    if (app && typeof app.showNotification === 'function') {
        app.showNotification('error', 'Promise Error', 'A promise rejection occurred');
    }
});