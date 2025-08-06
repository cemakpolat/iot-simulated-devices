import time
from typing import Dict, Any, Optional, List, Tuple, Set

from enocean_gateway.config.eep_profile_loader import EEPProfileLoader
from enocean_gateway.storage.sqlite_repository import SQLiteDeviceRepository
from enocean_gateway.utils.health_monitor import HealthMonitor, HealthCheck
from enocean_gateway.utils.logger import Logger
from enocean_gateway.connections.serial_connection import SerialConnection
from enocean_gateway.connections.mqtt_connection import MQTTConnection
from enocean_gateway.protocol.packet_parser import PacketParser, EnOceanPacket
from enocean_gateway.core.packet_processor import UnifiedPacketProcessor
from enocean_gateway.domain.models import DeviceId, DeviceConfig, UnknownDevice

from enocean_gateway.config.settings import Settings
from enocean_gateway.protocol.eep_profiles import EEPDecoder
from enocean_gateway.storage.repositories import DeviceRepository
from enocean_gateway.storage.json_repository import JSONDeviceRepository

# Monitoring components
from enocean_gateway.monitoring.metrics_collector import MetricsCollector
from enocean_gateway.monitoring.performance_monitor import PerformanceMonitor
from enocean_gateway.monitoring.web_metrics_endpoint import MetricsWebServer
from enocean_gateway.monitoring.packet_processor_wrapper import wrap_packet_processor_with_monitoring
from enocean_gateway.utils.enhanced_error_handling import ErrorHandlingFactory


class UnifiedSystemFactory:
    """Factory for creating unified EnOcean systems with different storage backends"""

    @staticmethod
    def create_json_system(settings: Settings, devices_file: str,
                           eep_loader: EEPProfileLoader) -> 'UnifiedEnOceanSystem':
        """Create system with JSON storage"""
        logger = Logger(debug=settings.DEBUG)
        device_repository = JSONDeviceRepository(devices_file, logger)
        return UnifiedSystemFactory._create_system_common(settings, device_repository, eep_loader, logger)

    @staticmethod
    def create_sqlite_system(settings: Settings, db_file: str, eep_loader: EEPProfileLoader) -> 'UnifiedEnOceanSystem':
        """Create system with SQLite storage"""
        logger = Logger(debug=settings.DEBUG)
        device_repository = SQLiteDeviceRepository(db_file, logger)
        return UnifiedSystemFactory._create_system_common(settings, device_repository, eep_loader, logger)

    @staticmethod
    def _create_error_handling(settings: Settings, logger: Logger) -> Dict[str, Any]:
        """Create error handling components with integrated DLQ"""
        return ErrorHandlingFactory.create_enhanced_error_handling(settings, logger)
    
    @staticmethod
    def _create_system_common(settings: Settings, device_repository: DeviceRepository,
                              eep_loader: EEPProfileLoader, logger: Logger) -> 'UnifiedEnOceanSystem':
        """Common system creation logic"""
        # Create connections
        serial_conn = SerialConnection(settings.PORT, settings.BAUD_RATE, logger)
        mqtt_conn = MQTTConnection(
            settings.MQTT_BROKER, settings.MQTT_PORT,
            settings.MQTT_CLIENT_ID, settings.MQTT_TOPIC, logger
        )

        # Create EEP decoder
        eep_decoder = EEPDecoder(logger)

        # Initialize monitoring
        monitoring_enabled = getattr(settings, 'MONITORING_ENABLED', True)
        metrics_port = getattr(settings, 'METRICS_PORT', 9090)

        # Create monitoring components
        metrics_collector = None
        performance_monitor = None
        health_monitor = None
        metrics_web_server = None

        if monitoring_enabled:
            metrics_collector = MetricsCollector(logger, "data/metrics.json")
            performance_monitor = PerformanceMonitor(logger, metrics_collector)
            health_monitor = HealthMonitor(logger)
            metrics_web_server = MetricsWebServer(
                metrics_collector, performance_monitor, logger, port=metrics_port
            )

        # Create error handling components
        error_handling = UnifiedSystemFactory._create_error_handling(settings, logger)

        # Create packet processor
        packet_processor = UnifiedPacketProcessor(
            device_repository, eep_decoder, mqtt_conn, logger, eep_loader
        )

        # Wrap with monitoring if enabled
        packet_processor = wrap_packet_processor_with_monitoring(
            packet_processor, metrics_collector, error_handling, logger
        )

        # Create packet parser
        packet_parser = PacketParser(logger)

        return UnifiedEnOceanSystem(
            packet_parser, packet_processor, serial_conn, mqtt_conn, logger, eep_loader,
            metrics_collector=metrics_collector,
            performance_monitor=performance_monitor,
            health_monitor=health_monitor,
            metrics_web_server=metrics_web_server,
            error_handling=error_handling
        )



class UnifiedEnOceanSystem:
    """Main unified EnOcean system with integrated monitoring and error handling"""

    def __init__(self, packet_parser: PacketParser, packet_processor: UnifiedPacketProcessor,
                 serial_connection: SerialConnection, mqtt_connection: MQTTConnection,
                 logger: Logger, eep_loader: EEPProfileLoader,
                 metrics_collector: Optional[MetricsCollector] = None,
                 performance_monitor: Optional[PerformanceMonitor] = None,
                 health_monitor: Optional[HealthMonitor] = None,
                 metrics_web_server: Optional[MetricsWebServer] = None,
                 error_handling: Optional[Dict[str, Any]] = None):

        # Core components
        self.packet_parser = packet_parser
        self.packet_processor = packet_processor
        self.serial_connection = serial_connection
        self.mqtt_connection = mqtt_connection
        self.logger = logger
        self.eep_loader = eep_loader

        # Monitoring components (NEW)
        self.metrics_collector = metrics_collector
        self.performance_monitor = performance_monitor
        self.health_monitor = health_monitor
        self.metrics_web_server = metrics_web_server

        # Error handling components (NEW)
        self.error_handling = error_handling or {}

        # System state
        self.running = False
        self.start_time = None

        # Initialize monitoring if available
        if self.metrics_collector:
            self._setup_monitoring()

    def _setup_monitoring(self):
        """Setup monitoring and health checks"""
        if not self.metrics_collector:
            return

        # Register gateway-specific metrics
        self.packet_counter = self.metrics_collector.register_counter(
            "enocean_packets_processed_total", "Total EnOcean packets processed"
        )
        self.device_gauge = self.metrics_collector.register_gauge(
            "enocean_devices_registered", "Number of registered devices"
        )
        self.unknown_device_gauge = self.metrics_collector.register_gauge(
            "enocean_devices_unknown", "Number of unknown devices"
        )
        self.processing_histogram = self.metrics_collector.register_histogram(
            "enocean_packet_processing_duration_seconds",
            "Time to process packets",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )
        self.error_counter = self.metrics_collector.register_counter(
            "enocean_errors_total", "Total system errors"
        )

        # Setup health checks
        if self.health_monitor:
            self._register_health_checks()

        self.logger.info("📊 Monitoring system initialized")

    def _register_health_checks(self):
        """Register health checks for system components - SIMPLIFIED"""
        if not self.health_monitor:
            return

        # Serial connection health check - simplified
        def check_serial_health() -> Dict[str, Any]:
            return {
                "healthy": self.serial_connection.is_connected(),
                "connection_status": "connected" if self.serial_connection.is_connected() else "disconnected",
                "port": self.serial_connection.port
            }

        # MQTT connection health check - simplified  
        def check_mqtt_health() -> Dict[str, Any]:
            return {
                "healthy": self.mqtt_connection.is_connected(),
                "connection_status": "connected" if self.mqtt_connection.is_connected() else "disconnected",
                "broker": self.mqtt_connection.broker
            }

        # Device repository health check - simplified
        def check_repository_health() -> Dict[str, Any]:
            devices = self.packet_processor.device_repository.get_all_devices()
            return {
                "healthy": True,
                "device_count": len(devices),
                "repository_type": type(self.packet_processor.device_repository).__name__
            }

        # Packet processing health check - simplified
        def check_packet_processing_health() -> Dict[str, Any]:
            stats = self.get_statistics()
            return {
                "healthy": True,
                "packets_processed": stats.get("total_packets_processed", 0),
                "unknown_devices": stats.get("unknown_devices_detected", 0),
                "registered_devices": stats.get("total_devices", 0)
            }

        # Register health checks
        health_checks = [
            HealthCheck("serial_connection", check_serial_health, interval=30, critical=True),
            HealthCheck("mqtt_connection", check_mqtt_health, interval=60, critical=False),
            HealthCheck("device_repository", check_repository_health, interval=120, critical=True),
            HealthCheck("packet_processing", check_packet_processing_health, interval=30, critical=True)
        ]

        for health_check in health_checks:
            self.health_monitor.register_check(health_check)

        self.logger.info("🏥 Health checks registered")

    def start(self) -> bool:
        """Start the unified system with monitoring"""
        try:
            self.start_time = time.time()

            # Start monitoring first
            if self.performance_monitor:
                self.performance_monitor.start_monitoring(interval=30)

            if self.health_monitor:
                self.health_monitor.start_monitoring()

            if self.metrics_web_server:
                self.metrics_web_server.start_background()

            # Connect to serial with circuit breaker protection
            serial_circuit_breaker = self.error_handling.get("serial_circuit_breaker")
            if serial_circuit_breaker:
                try:
                    serial_connected = serial_circuit_breaker.call(self.serial_connection.connect)
                except CircuitBreakerOpenException:
                    self.logger.error("Serial connection circuit breaker is open")
                    return False
            else:
                serial_connected = self.serial_connection.connect()

            if not serial_connected:
                self.logger.failure("Failed to connect to serial port")
                if self.error_counter:
                    self.error_counter.increment()
                return False

            # Connect to MQTT (non-critical)
            try:
                if not self.mqtt_connection.connect():
                    self.logger.warning("MQTT connection failed, continuing without MQTT")
            except Exception as e:
                self.logger.warning(f"MQTT connection error: {e}")

            self.running = True

            # Update monitoring metrics
            if self.metrics_collector:
                self._update_device_metrics()

            self.logger.success("🚀 Unified EnOcean system started with monitoring")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            if self.error_counter:
                self.error_counter.increment()
            return False

    def stop(self):
        """Stop the unified system and monitoring"""
        self.running = False

        # Stop enhanced error handling
        for name, handler in self.error_handling.items():
            if hasattr(handler, 'stop'):
                try:
                    handler.stop()
                    self.logger.info(f"Stopped {name} error handler")
                except Exception as e:
                    self.logger.warning(f"Error stopping {name} handler: {e}")

        # Stop monitoring components (existing code)
        if self.performance_monitor:
            self.performance_monitor.stop_monitoring()

        if self.health_monitor:
            self.health_monitor.stop_monitoring()

        # Save final metrics
        if self.metrics_collector:
            self.metrics_collector.save_to_storage()

        # Disconnect from connections
        if self.serial_connection:
            self.serial_connection.disconnect()

        if self.mqtt_connection:
            self.mqtt_connection.disconnect()

    def get_dlq_statistics(self) -> Dict[str, Any]:
        """Get Dead Letter Queue statistics"""
        dlq_stats = {}
        
        for name, handler in self.error_handling.items():
            if hasattr(handler, 'get_dlq_messages'):
                messages = handler.get_dlq_messages()
                dlq_stats[name] = {
                    "message_count": len(messages),
                    "recent_messages": messages[-5:] if messages else [],
                    "statistics": handler.get_statistics()
                }
        
        return dlq_stats

    def get_dlq_messages(self, handler_name: str = None) -> Dict[str, list]:
        """Get DLQ messages for inspection"""
        if handler_name:
            handler = self.error_handling.get(handler_name)
            if handler and hasattr(handler, 'get_dlq_messages'):
                return {handler_name: handler.get_dlq_messages()}
            return {}
        
        # Get all DLQ messages
        all_messages = {}
        for name, handler in self.error_handling.items():
            if hasattr(handler, 'get_dlq_messages'):
                all_messages[name] = handler.get_dlq_messages()
        
        return all_messages
    
    def process_packets_from_serial(self) -> int:
        """Read and process packets from serial connection with enhanced error handling"""
        if not self.running:
            return 0

        packet_count = 0
        processing_start = time.time()

        try:
            # Use enhanced error handling if available
            serial_handler = self.error_handling.get("serial")
            if serial_handler:
                packet_count = serial_handler.execute_with_full_error_handling(
                    self._process_packets_internal,
                    "process_packets_from_serial"
                )
            else:
                # Fallback to original method
                packet_count = self._process_packets_internal()

            # Record processing metrics (existing code)
            if self.processing_histogram:
                processing_duration = time.time() - processing_start
                self.processing_histogram.observe(processing_duration)

            if self.packet_counter:
                self.packet_counter.increment(packet_count)

        except Exception as e:
            self.logger.error(f"Error processing packets: {e}")
            if self.error_counter:
                self.error_counter.increment()

        return packet_count

    def _process_packets_internal(self) -> int:
        """Internal packet processing method"""
        raw_data = self.serial_connection.read_available()
        if not raw_data:
            return 0

        packets = self.packet_parser.parse_buffer(raw_data)
        for packet in packets:
            self.packet_processor.process_packet(packet)

        return len(packets)

    def simulate_packet(self, device_id: str, packet_data: str) -> bool:
        """Simulate a packet for testing with monitoring"""
        try:
            processing_start = time.time()

            # Convert hex string to bytes
            raw_data = bytes.fromhex(packet_data.replace(' ', '').replace(':', ''))

            # Create mock packet
            rorg = raw_data[0] if raw_data else 0
            mock_packet = EnOceanPacket(
                raw_packet=raw_data,
                rorg=rorg,
                data=raw_data,
                sender_id=device_id,
                status=0,
                timestamp=time.time()
            )

            # Process the packet
            result = self.packet_processor.process_packet(mock_packet)

            # Record metrics
            if self.processing_histogram:
                processing_duration = time.time() - processing_start
                self.processing_histogram.observe(processing_duration)

            if self.packet_counter:
                self.packet_counter.increment()

            return result is not None

        except Exception as e:
            self.logger.error(f"Failed to simulate packet: {e}")
            if self.error_counter:
                self.error_counter.increment()
            return False

    def register_device(self, device_id: str, name: str, eep_profile: str, **kwargs) -> bool:
        """Register a device manually with enhanced error handling"""
        try:
            # Use enhanced database error handling if available
            db_handler = self.error_handling.get("database")
            if db_handler:
                result = db_handler.execute_with_full_error_handling(
                    self.packet_processor.register_unknown_device,
                    "register_device",
                    device_id, name, eep_profile, **kwargs
                )
            else:
                # Fallback to original method
                result = self.packet_processor.register_unknown_device(
                    device_id, name, eep_profile, **kwargs
                )

            # Update device metrics (existing code)
            if result and self.metrics_collector:
                self._update_device_metrics()
                self.metrics_collector.record_custom_metric(
                    "device_registration_event", 1,
                    tags={"device_id": device_id, "eep_profile": eep_profile}
                )

            return result

        except Exception as e:
            self.logger.error(f"Failed to register device: {e}")
            if self.error_counter:
                self.error_counter.increment()
            return False

    def remove_device(self, device_id: str) -> bool:
        """Remove a device with enhanced error handling"""
        try:
            device_id_obj = DeviceId(device_id)

            # Use enhanced database error handling if available
            db_handler = self.error_handling.get("database")
            if db_handler:
                result = db_handler.execute_with_full_error_handling(
                    self.packet_processor.device_repository.remove_device,
                    "remove_device",
                    device_id_obj
                )
            else:
                # Fallback to original method
                result = self.packet_processor.device_repository.remove_device(device_id_obj)

            # Update metrics
            if result and self.metrics_collector:
                self._update_device_metrics()

            return result

        except ValueError:
            return False
        except Exception as e:
            self.logger.error(f"Failed to remove device: {e}")
            if self.error_counter:
                self.error_counter.increment()
            return False

    def list_devices(self) -> List[DeviceConfig]:
        """List all registered devices"""
        try:
            # Try the standard method name first
            if hasattr(self.packet_processor.device_repository, 'get_all_devices'):
                return self.packet_processor.device_repository.get_all_devices()
            # Fallback to alternative method name
            elif hasattr(self.packet_processor.device_repository, 'list_devices'):
                return self.packet_processor.device_repository.list_devices()
            else:
                self.logger.warning("No device listing method found in repository")
                return []
        except Exception as e:
            self.logger.error(f"Failed to list devices: {e}")
            return []

    def get_unknown_devices(self) -> List[UnknownDevice]:
        """Get unknown devices for discovery dashboard"""
        try:
            return self.packet_processor.discovery_engine.get_unknown_devices()
        except Exception as e:
            self.logger.error(f"Failed to get unknown devices: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics including DLQ data"""
        try:
            # Get base statistics (existing method)
            base_stats = {
                "system_uptime": time.time() - self.start_time if self.start_time else 0,
                "running": self.running
            }

            # Add packet processor stats
            if hasattr(self.packet_processor, 'get_statistics'):
                base_stats.update(self.packet_processor.get_statistics())

            # Add monitoring data if available
            monitoring_stats = {}
            if self.metrics_collector:
                monitoring_stats = {
                    "monitoring": {
                        "metrics_summary": self.metrics_collector.get_summary(),
                        "uptime_seconds": time.time() - self.start_time if self.start_time else 0
                    }
                }

            if self.performance_monitor:
                monitoring_stats["performance"] = self.performance_monitor.get_performance_summary()

            if self.health_monitor:
                monitoring_stats["health"] = self.health_monitor.get_health_status()

            # Add enhanced error handling stats (NEW)
            error_handling_stats = {}
            for name, component in self.error_handling.items():
                if hasattr(component, 'get_statistics'):
                    error_handling_stats[name] = component.get_statistics()

            return {
                **base_stats,
                **monitoring_stats,
                "error_handling": error_handling_stats
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        if self.health_monitor:
            return self.health_monitor.get_health_status()
        else:
            return {
                "status": "unknown",
                "message": "Health monitoring not enabled"
            }

    def ignore_unknown_device(self, device_id: str) -> bool:
        """Ignore an unknown device"""
        try:
            result = self.packet_processor.ignore_unknown_device(device_id)

            # Update metrics
            if result and self.metrics_collector:
                self._update_device_metrics()

            return result
        except Exception as e:
            self.logger.error(f"Failed to ignore unknown device: {e}")
            return False

    def get_all_unknown_device_ids(self) -> Set[str]:
        """Returns a set of all device IDs currently in the unknown list."""
        if not hasattr(self, 'packet_processor'):
            return set()
        try:
            unknown_devices = self.packet_processor.discovery_engine._load_unknown_devices()
            return set(unknown_devices.keys())
        except Exception as e:
            self.logger.error(f"Failed to get unknown device IDs: {e}")
            return set()

    def clean_unknown_devices(self, registered_ids: Set[str]) -> int:
        """Removes any device IDs from the unknown list that are now registered."""
        if not hasattr(self, 'packet_processor'):
            return 0
        try:
            discovery_engine = self.packet_processor.discovery_engine
            unknown_devices = discovery_engine._load_unknown_devices()

            # Find which unknown devices are in the registered list
            ids_to_remove = set(unknown_devices.keys()) & registered_ids

            if not ids_to_remove:
                return 0

            # Remove them and save the updated list
            for device_id in ids_to_remove:
                del unknown_devices[device_id]

            discovery_engine._save_unknown_devices(unknown_devices)
            self.logger.info(f"Cleaned {len(ids_to_remove)} registered devices from the unknown list.")

            # Update metrics
            if self.metrics_collector:
                self._update_device_metrics()

            return len(ids_to_remove)
        except Exception as e:
            self.logger.error(f"Failed to clean unknown devices: {e}")
            return 0

    def _update_device_metrics(self):
        """Update device-related metrics"""
        if not self.metrics_collector:
            return

        try:
            # Update registered device count
            devices = self.list_devices()
            self.device_gauge.set(len(devices))

            # Update unknown device count
            unknown_devices = self.get_unknown_devices()
            self.unknown_device_gauge.set(len(unknown_devices))

        except Exception as e:
            self.logger.warning(f"Failed to update device metrics: {e}")

    def export_metrics(self, filepath: str) -> bool:
        """Export current metrics to file"""
        if not self.metrics_collector:
            self.logger.warning("Metrics collector not available")
            return False

        try:
            import json

            metrics_data = {
                "export_timestamp": time.time(),
                "system_statistics": self.get_statistics(),
                "health_status": self.get_health_status(),
                "prometheus_format": self.metrics_collector.get_prometheus_format()
            }

            with open(filepath, 'w') as f:
                json.dump(metrics_data, f, indent=2)

            self.logger.info(f"📊 Metrics exported to {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            return False


# ============================================================================
# Configuration Management with Monitoring
# ============================================================================

def create_system_from_config(config_file: str, storage_type: str,
                              eep_loader: EEPProfileLoader) -> UnifiedEnOceanSystem:
    """Create unified system with dynamic storage selection from config"""
    from dotenv import load_dotenv
    import os

    load_dotenv(config_file)
    settings = Settings()

    if not settings.validate():
        raise ValueError("Invalid settings configuration")

    # Get storage type from environment or parameter
    storage_type = storage_type or os.getenv('STORAGE_TYPE', 'json').lower()
    devices_file = os.getenv('DEVICES_FILE', 'devices.json')

    # Dynamic storage selection
    if storage_type == 'json':
        return UnifiedSystemFactory.create_json_system(settings, devices_file, eep_loader)
    elif storage_type == 'sqlite':
        return UnifiedSystemFactory.create_sqlite_system(settings, devices_file, eep_loader)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")

