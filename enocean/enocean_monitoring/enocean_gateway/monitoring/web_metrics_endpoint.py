# monitoring/web_metrics_endpoint.py
import time
import json
from typing import Dict, Any
from flask import Flask, Response, jsonify
from enocean_gateway.monitoring.metrics_collector import MetricsCollector
from enocean_gateway.monitoring.performance_monitor import PerformanceMonitor


class MetricsWebServer:
    """Web server for exposing metrics via HTTP"""

    def __init__(self, metrics_collector: MetricsCollector, performance_monitor: PerformanceMonitor,
                 logger, port: int = 9090):
        self.metrics = metrics_collector
        self.performance = performance_monitor
        self.logger = logger
        self.port = port

        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup web routes for metrics"""

        @self.app.route('/metrics')
        def metrics_endpoint():
            """Prometheus-compatible metrics endpoint"""
            prometheus_data = self.metrics.get_prometheus_format()
            return Response(prometheus_data, mimetype='text/plain')

        @self.app.route('/metrics/json')
        def metrics_json():
            """JSON format metrics"""
            return jsonify(self.metrics.get_all_metrics())

        @self.app.route('/health')
        def health_check():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "timestamp": time.time(),
                "uptime": time.time() - self.metrics._collection_start
            })

        @self.app.route('/performance')
        def performance_summary():
            """Performance metrics summary"""
            return jsonify(self.performance.get_performance_summary())

        @self.app.route('/metrics/summary')
        def metrics_summary():
            """High-level metrics summary"""
            return jsonify(self.metrics.get_summary())

        @self.app.route('/metrics/reset', methods=['POST'])
        def reset_counters():
            """Reset all counter metrics"""
            self.metrics.reset_all_counters()
            return jsonify({"status": "counters_reset", "timestamp": time.time()})

    def start(self, debug: bool = False):
        """Start the metrics web server"""
        try:
            self.logger.info(f"Starting metrics web server on port {self.port}")
            self.app.run(host='0.0.0.0', port=self.port, debug=debug, threaded=True)
        except Exception as e:
            self.logger.error(f"Failed to start metrics web server: {e}")

    def start_background(self):
        """Start metrics server in background thread"""
        import threading

        server_thread = threading.Thread(
            target=self.start,
            kwargs={"debug": False},
            daemon=True
        )
        server_thread.start()
        self.logger.info(f"Metrics web server started in background on port {self.port}")


# Integration with EnOcean Gateway
class GatewayMetricsIntegration:
    """Integration layer for EnOcean Gateway metrics"""

    def __init__(self, gateway_system, logger):
        self.gateway = gateway_system
        self.logger = logger

        # Initialize monitoring components
        self.metrics_collector = MetricsCollector(logger, "data/metrics.json")
        self.performance_monitor = PerformanceMonitor(logger, self.metrics_collector)
        self.web_server = MetricsWebServer(
            self.metrics_collector,
            self.performance_monitor,
            logger,
            port=9090
        )

        # Setup gateway-specific metrics
        self._setup_gateway_metrics()

        # Hook into gateway events
        self._setup_event_hooks()

    def _setup_gateway_metrics(self):
        """Setup EnOcean Gateway specific metrics"""
        # Device metrics
        self.device_counter = self.metrics_collector.register_counter(
            "enocean_devices_registered_total",
            "Total number of registered EnOcean devices"
        )

        self.unknown_device_gauge = self.metrics_collector.register_gauge(
            "enocean_devices_unknown_current",
            "Current number of unknown devices"
        )

        # Packet metrics
        self.packet_processing_histogram = self.metrics_collector.register_histogram(
            "enocean_packet_processing_duration_seconds",
            "Time spent processing EnOcean packets",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )

        self.discovery_histogram = self.metrics_collector.register_histogram(
            "enocean_discovery_analysis_duration_seconds",
            "Time spent analyzing unknown devices",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )

        # EEP Profile metrics
        self.eep_profile_counter = self.metrics_collector.register_counter(
            "enocean_packets_by_eep_total",
            "Total packets received by EEP profile"
        )

        # Error metrics
        self.decode_error_counter = self.metrics_collector.register_counter(
            "enocean_decode_errors_total",
            "Total packet decode errors"
        )

        self.serial_error_counter = self.metrics_collector.register_counter(
            "enocean_serial_errors_total",
            "Total serial communication errors"
        )

    def _setup_event_hooks(self):
        """Setup hooks into gateway events for metrics collection"""

        # This would integrate with your actual gateway event system
        # Example implementation:

        def on_packet_processed(device_id: str, processing_time: float, success: bool):
            """Called when a packet is processed"""
            self.packet_processing_histogram.observe(processing_time)

            if success:
                self.metrics_collector.get_counter("packets_processed_total").increment()
            else:
                self.metrics_collector.get_counter("packets_failed_total").increment()

        def on_device_registered(device_id: str, eep_profile: str):
            """Called when a device is registered"""
            self.device_counter.increment()
            self.metrics_collector.record_custom_metric(
                "device_registration_event",
                1,
                tags={"device_id": device_id, "eep_profile": eep_profile}
            )

        def on_unknown_device_discovered(device_id: str, analysis_time: float):
            """Called when unknown device is discovered"""
            self.discovery_histogram.observe(analysis_time)
            self.metrics_collector.get_counter("packets_unknown_total").increment()

        def on_decode_error(error_type: str, device_id: str = None):
            """Called when packet decode fails"""
            self.decode_error_counter.increment()
            self.metrics_collector.record_custom_metric(
                "decode_error_event",
                1,
                tags={"error_type": error_type, "device_id": device_id or "unknown"}
            )

        # Store event handlers for gateway to use
        self.event_handlers = {
            "packet_processed": on_packet_processed,
            "device_registered": on_device_registered,
            "unknown_device_discovered": on_unknown_device_discovered,
            "decode_error": on_decode_error
        }

    def start_monitoring(self):
        """Start all monitoring components"""
        # Start performance monitoring
        self.performance_monitor.start_monitoring(interval=30)

        # Start metrics web server
        self.web_server.start_background()

        # Update device metrics from current gateway state
        self._update_device_metrics()

        self.logger.info("Gateway metrics monitoring started")

    def stop_monitoring(self):
        """Stop all monitoring components"""
        self.performance_monitor.stop_monitoring()
        self.logger.info("Gateway metrics monitoring stopped")

    def _update_device_metrics(self):
        """Update metrics based on current gateway state"""
        try:
            # Update registered device count
            if hasattr(self.gateway, 'device_repository'):
                devices = self.gateway.device_repository.get_all_devices()
                self.metrics_collector.get_gauge("devices_registered").set(len(devices))

            # Update unknown device count
            if hasattr(self.gateway, 'discovery_engine'):
                unknown_devices = self.gateway.discovery_engine.get_unknown_devices()
                self.unknown_device_gauge.set(len(unknown_devices))

        except Exception as e:
            self.logger.warning(f"Failed to update device metrics: {e}")

    def get_gateway_health(self) -> Dict[str, Any]:
        """Get comprehensive gateway health status"""
        health_data = {
            "timestamp": time.time(),
            "status": "healthy",  # Would be determined by actual health checks
            "metrics_summary": self.metrics_collector.get_summary(),
            "performance": self.performance_monitor.get_performance_summary(),
            "components": {
                "packet_processor": "healthy",  # Would check actual component status
                "discovery_engine": "healthy",
                "device_repository": "healthy",
                "serial_connection": "healthy"
            }
        }

        return health_data

    def export_metrics_snapshot(self, filepath: str):
        """Export current metrics to file"""
        try:
            metrics_data = {
                "export_timestamp": time.time(),
                "gateway_health": self.get_gateway_health(),
                "all_metrics": self.metrics_collector.get_all_metrics(),
                "prometheus_format": self.metrics_collector.get_prometheus_format()
            }

            with open(filepath, 'w') as f:
                json.dump(metrics_data, f, indent=2)

            self.logger.info(f"Metrics snapshot exported to {filepath}")

        except Exception as e:
            self.logger.error(f"Failed to export metrics snapshot: {e}")


# Example usage and integration
def setup_gateway_monitoring(gateway_config, gateway_system, logger):
    """Setup comprehensive monitoring for EnOcean Gateway"""

    # Create monitoring integration
    monitoring = GatewayMetricsIntegration(gateway_system, logger)

    # Start monitoring
    monitoring.start_monitoring()

    # Setup periodic metrics export (optional)
    if gateway_config.get("export_metrics", False):
        import threading
        import time

        def periodic_export():
            while True:
                time.sleep(3600)  # Export every hour
                timestamp = int(time.time())
                filepath = f"exports/metrics_{timestamp}.json"
                monitoring.export_metrics_snapshot(filepath)

        export_thread = threading.Thread(target=periodic_export, daemon=True)
        export_thread.start()

    return monitoring
