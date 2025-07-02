// dashboard/static/js/dashboard.js

// Initialize Socket.IO client, connecting to the current host
const socket = io(); 

// --- Constants ---
const MAX_ALERTS = 10;
const MAX_PREDICTIONS = 20; // Keep last 20 predictions for the chart

// --- Global State & Managers (Singletons for simplicity) ---
let temperatureChartInstance; // Stores Chart.js instance

// Data storage arrays
let alertHistory = []; // Array to hold recent alerts
let predictionHistory = []; // Array to hold historical predictions for the chart

// --- UI Element Selectors ---
const uiElements = {
    statusIndicator: document.getElementById('status-indicator'),
    statusText: document.querySelector('#status-indicator span:last-child'),
    currentTemperature: document.getElementById('current-temperature'),
    temperatureStatus: document.getElementById('temperature-status'),
    currentHumidity: document.getElementById('current-humidity'),
    humidityStatus: document.getElementById('humidity-status'),
    currentAqi: document.getElementById('current-aqi'),
    airQualityStatus: document.getElementById('air-quality-status'),
    currentOccupancy: document.getElementById('current-occupancy'),
    occupancyStatus: document.getElementById('occupancy-status'),
    hvacState: document.getElementById('hvac-state'),
    targetTemperature: document.getElementById('target-temperature'),
    energyConsumption: document.getElementById('energy-consumption'),
    predictedEnergy: document.getElementById('predicted-energy'), // This element in HTML is `id="energy-consumption"` not `predicted-energy` - I've updated HTML below.
    alertsList: document.getElementById('alerts-list'),
    tempInput: document.getElementById('temp-input'),
    temperatureChartCanvas: document.getElementById('temperatureChart'),
};

// --- Managers (SRP Applied) ---

class ConnectionManager {
    constructor(socket, statusIndicatorElement, statusTextElement) {
        this.socket = socket;
        this.statusIndicatorElement = statusIndicatorElement;
        this.statusTextElement = statusTextElement;
        this._setupListeners();
    }

    _setupListeners() {
        this.socket.on('connect', this._handleConnect.bind(this));
        this.socket.on('disconnect', this._handleDisconnect.bind(this));
    }

    _handleConnect() {
        console.log('Connected to dashboard server WebSocket');
        this.statusIndicatorElement.classList.remove('bg-yellow-400', 'bg-red-600', 'status-pulse');
        this.statusIndicatorElement.classList.add('bg-green-500'); // Green for online
        this.statusTextElement.textContent = 'Online';
    }

    _handleDisconnect() {
        console.log('Disconnected from dashboard server WebSocket');
        this.statusIndicatorElement.classList.remove('bg-green-500');
        this.statusIndicatorElement.classList.add('bg-red-600', 'status-pulse'); // Red and pulsing for offline
        this.statusTextElement.textContent = 'Offline';
    }
}

class DashboardUIManager {
    constructor(elements) {
        this.elements = elements;
    }

    updateCurrentReadings(data) {
        if (data.temperature) {
            this.elements.currentTemperature.textContent = `${data.temperature.value}°C`;
            this.elements.temperatureStatus.textContent = `Status: ${data.temperature.status || 'Normal'}`;
        }
        if (data.humidity) {
            this.elements.currentHumidity.textContent = `${data.humidity.value}%`;
            this.elements.humidityStatus.textContent = `Status: ${data.humidity.status || 'Normal'}`;
        }
        if (data.air_quality) {
            this.elements.currentAqi.textContent = `${data.air_quality.aqi} AQI`; // Added AQI unit
            this.elements.airQualityStatus.textContent = `Quality: ${data.air_quality.quality}`;
        }
        if (data.occupancy) {
            this.elements.currentOccupancy.textContent = data.occupancy.occupied ? 'Occupied' : 'Vacant';
            this.elements.occupancyStatus.textContent = `Confidence: ${data.occupancy.confidence}`;
        }
    }

    updateHvacStatus(data) {
        if (data.hvac) {
            this.elements.hvacState.textContent = data.hvac.state;
            this.elements.targetTemperature.textContent = `${data.hvac.target_temperature}°C`;
            // Ensure energy consumption is always formatted
            this.elements.energyConsumption.textContent = `${data.hvac.energy_consumption.toFixed(2)} kWh`;
            // The predicted energy element is now distinct
            if (this.elements.predictedEnergy && data.predictions && data.predictions.length > 0) {
                // Use a prediction from the AI model, e.g., the first prediction
                this.elements.predictedEnergy.textContent = `${data.predictions[0].toFixed(2)} °C (next hour temp)`; 
            } else if (this.elements.predictedEnergy) {
                 this.elements.predictedEnergy.textContent = `--`;
            }
        }
    }
}

class AlertsManager {
    constructor(alertsListElement, maxAlerts) {
        this.alertsListElement = alertsListElement;
        this.maxAlerts = maxAlerts;
        this.alertHistory = []; // Local state for alerts
    }

    // Helper to clear "No active alerts" message
    _clearNoAlertsMessage() {
        const noAlertsDiv = this.alertsListElement.querySelector('.no-alerts-message');
        if (noAlertsDiv) {
            noAlertsDiv.remove();
        }
    }

    displayAlert(alertData) {
        console.log("AlertsManager: Raw alertData received:", alertData); 

        // Defensive check
        if (!alertData || typeof alertData !== 'object' || !alertData.timestamp || !alertData.message) {
            console.error("AlertsManager: Invalid alert data received or missing properties. Skipping display.", alertData);
            return; 
        }

        this._clearNoAlertsMessage(); // Clear initial message

        const li = document.createElement('li');
        let timestamp_display;
        try {
            timestamp_display = new Date(alertData.timestamp).toLocaleTimeString();
        } catch (e) {
            console.warn("AlertsManager: Failed to parse alert timestamp:", alertData.timestamp, e);
            timestamp_display = "Invalid Time";
        }

        li.textContent = `${timestamp_display} - ${alertData.message}`;
        
        // --- FIX START ---
        // Determine the severity classes as a single string
        const severityClasses = 
            alertData.severity === 'critical' ? 'bg-red-50 text-red-700 border-red-500' :
            alertData.severity === 'high' ? 'bg-yellow-50 text-yellow-700 border-yellow-500' :
            alertData.severity === 'medium' ? 'bg-blue-50 text-blue-700 border-blue-500' :
            'bg-gray-50 text-gray-700 border-gray-500'; // Default info/low

        // Add base classes and then spread the severity classes
        li.classList.add(
            'p-3', 'rounded-lg', 'text-sm', 'font-medium', 'break-words', 'border-l-4',
            ...severityClasses.split(' ') // Split the string into an array and spread them
        ); 
        // --- FIX END ---

        this.alertsListElement.prepend(li); // Add to the beginning (newest first)

        // Manage alert history (keep only MAX_ALERTS)
        this.alertHistory.unshift(alertData); // Add new alert to the front
        if (this.alertHistory.length > this.maxAlerts) {
            this.alertHistory.pop(); // Remove the oldest alert from array
            if (this.alertsListElement.lastChild && !this.alertsListElement.lastChild.classList.contains('no-alerts-message')) {
                // Ensure we don't try to remove the "no-alerts-message" placeholder if it somehow re-appeared
                this.alertsListElement.lastChild.remove(); // Remove oldest alert from DOM
            }
        }
    }

    loadInitialAlerts(alerts) {
        this._clearNoAlertsMessage(); // Clear initial message
        this.alertHistory = []; // Reset local history
        this.alertsListElement.innerHTML = ''; // Clear DOM

        if (alerts && alerts.length > 0) {
            // Display oldest first if initial load (optional: reverse order)
            // For consistency with push, let's prepend initial alerts as well.
            alerts.slice(0, this.maxAlerts).reverse().forEach(alert => this.displayAlert(alert));
        } else {
            // Only add the placeholder if there are truly no alerts
            const noAlertsDiv = document.createElement('div');
            noAlertsDiv.className = 'text-center py-4 text-dark-400 no-alerts-message';
            noAlertsDiv.textContent = 'No active alerts';
            this.alertsListElement.appendChild(noAlertsDiv);
        }
    }
}



class TemperatureChartManager {
    constructor(canvasElement, maxPredictions) {
        this.canvasElement = canvasElement;
        this.maxPredictions = maxPredictions;
        this.chartInstance = null;
        this.predictionHistory = []; // Local state for chart data
    }

    _initChart(labels, values) {
        const ctx = this.canvasElement.getContext('2d');
        this.chartInstance = new Chart(ctx, {
            type: 'line', 
            data: {
                labels: labels,
                datasets: [{
                    label: 'Predicted Temperature (°C)',
                    data: values,
                    borderColor: 'rgb(14, 165, 233)', // primary-500
                    backgroundColor: 'rgba(14, 165, 233, 0.2)',
                    tension: 0.3, // Smooth the line
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, 
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Temperature (°C)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hours Ahead'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#334155' // dark-700
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y + '°C';
                            }
                        }
                    }
                }
            }
        });
    }

    updateChart(newPredictions) {
        // Add new predictions, keeping only the last MAX_PREDICTIONS
        this.predictionHistory = this.predictionHistory.concat(newPredictions);
        if (this.predictionHistory.length > this.maxPredictions) {
            this.predictionHistory = this.predictionHistory.slice(-this.maxPredictions);
        }

        const labels = this.predictionHistory.map((_, i) => `Hour ${i + 1}`);
        const values = this.predictionHistory.map(p => parseFloat(p.toFixed(2))); // Ensure values are numbers and rounded

        if (this.chartInstance) {
            this.chartInstance.data.labels = labels;
            this.chartInstance.data.datasets[0].data = values;
            this.chartInstance.update();
        } else {
            this._initChart(labels, values);
        }
    }
}


// --- Main Dashboard Controller ---
class DashboardController {
    constructor(socket, uiElements) {
        this.socket = socket;
        this.uiElements = uiElements;
        this.connectionManager = new ConnectionManager(socket, uiElements.statusIndicator, uiElements.statusText);
        this.uiManager = new DashboardUIManager(uiElements);
        this.alertsManager = new AlertsManager(uiElements.alertsList, MAX_ALERTS);
        this.chartManager = new TemperatureChartManager(uiElements.temperatureChartCanvas, MAX_PREDICTIONS);
        
        this._setupSocketListeners();
        this._setupCommandListeners(); // This is the method causing the error
        this._initializeUI();
    }

    _setupSocketListeners() {
        this.socket.on('sensor_data', this._handleSensorData.bind(this));
        this.socket.on('command_result', this._handleCommandResult.bind(this));
        this.socket.on('alert', this._handleAlert.bind(this));
    }

    _setupCommandListeners() {

        const setTargetBtn = document.getElementById('set-target-btn');
        const heatBtn = document.getElementById('heat-btn');
        const coolBtn = document.getElementById('cool-btn');
        const offBtn = document.getElementById('off-btn');

        if (setTargetBtn) {
            setTargetBtn.addEventListener('click', () => this.sendCommand('set_target'));
        } else { console.warn("Button with ID 'set-target-btn' not found."); }
        
        if (heatBtn) {
            heatBtn.addEventListener('click', () => this.sendCommand('heat'));
        } else { console.warn("Button with ID 'heat-btn' not found."); }

        if (coolBtn) {
            coolBtn.addEventListener('click', () => this.sendCommand('cool'));
        } else { console.warn("Button with ID 'cool-btn' not found."); }

        if (offBtn) {
            offBtn.addEventListener('click', () => this.sendCommand('off'));
        } else { console.warn("Button with ID 'off-btn' not found."); }
        // --- FIX END ---
    }

    _initializeUI() {
        this.chartManager.updateChart([]); 
        this._fetchInitialAlerts();
    }

    _handleSensorData(data) {
        console.log('Controller: Received live sensor data:', data);
        this.uiManager.updateCurrentReadings(data);
        this.uiManager.updateHvacStatus(data);
        if (data.predictions && Array.isArray(data.predictions)) {
            this.chartManager.updateChart(data.predictions);
        }
    }

    _handleCommandResult(data) {
        console.log('Controller: Command result:', data);
        const alertBox = document.createElement('div');
        alertBox.className = `fixed bottom-4 right-4 p-3 rounded-lg shadow-lg text-white text-sm z-50 transition-all duration-300 transform translate-y-0 opacity-100 ${data.status === 'success' ? 'bg-green-500' : 'bg-red-500'}`;
        alertBox.textContent = data.message;
        document.body.appendChild(alertBox);
        setTimeout(() => {
            alertBox.classList.add('translate-y-full', 'opacity-0');
            alertBox.addEventListener('transitionend', () => alertBox.remove());
        }, 3000); 
    }

    _handleAlert(alertData) {
        console.warn('Controller: Received real-time alert:', alertData);
        this.alertsManager.displayAlert(alertData);
    }

    sendCommand(action) {
        let command = { action: action };
        if (action === 'set_target') {
            command.target_temperature = parseFloat(this.uiElements.tempInput.value);
            if (isNaN(command.target_temperature)) {
                alert('Please enter a valid target temperature.');
                return;
            }
        }
        console.log('Controller: Sending command:', command);
        this.socket.emit('send_command', { command: command });
    }

    _fetchInitialAlerts() {
        fetch('/dashboard/api/alerts')
            .then(response => response.json())
            .then(alerts => {
                this.alertsManager.loadInitialAlerts(alerts);
            })
            .catch(error => {
                console.error("Controller: Error fetching initial alerts:", error);
                this.alertsManager.displayAlert({
                    timestamp: new Date().toISOString(),
                    message: "Failed to load initial alerts. Check server logs.",
                    severity: "critical"
                });
            });
    }
}



// --- DOMContentLoaded: Initialize the main controller ---
document.addEventListener('DOMContentLoaded', () => {
    // Instantiate the controller, passing the socket and UI elements
    new DashboardController(socket, uiElements);
});