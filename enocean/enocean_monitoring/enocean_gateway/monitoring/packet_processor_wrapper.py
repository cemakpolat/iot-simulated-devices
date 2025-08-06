# monitoring/packet_processor_wrapper.py - Updated wrapper
"""
Monitoring wrapper for existing packet processor - provides monitoring without changing existing code
"""
import time


class MonitoringWrapper:
    """Wrapper that adds monitoring to existing packet processor without modifying it"""

    def __init__(self, packet_processor, metrics_collector=None, error_handling=None, logger=None):
        self.packet_processor = packet_processor
        self.metrics_collector = metrics_collector
        self.error_handling = error_handling or {}
        self.logger = logger

        # Setup metrics if available
        if self.metrics_collector:
            self._setup_metrics()

        # Inject metrics collector into the processor
        if hasattr(self.packet_processor, 'set_metrics_collector'):
            self.packet_processor.set_metrics_collector(self.metrics_collector)

    def _setup_metrics(self):
        """Setup monitoring metrics"""
        self.packet_counter = self.metrics_collector.get_counter("enocean_packets_processed_total")
        self.error_counter = self.metrics_collector.get_counter("enocean_errors_total")
        self.processing_histogram = self.metrics_collector.get_histogram("enocean_packet_processing_duration_seconds")

        if not self.packet_counter:
            self.packet_counter = self.metrics_collector.register_counter(
                "enocean_packets_processed_total", "Total packets processed"
            )
        if not self.error_counter:
            self.error_counter = self.metrics_collector.register_counter(
                "enocean_errors_total", "Total errors"
            )
        if not self.processing_histogram:
            self.processing_histogram = self.metrics_collector.register_histogram(
                "enocean_packet_processing_duration_seconds", "Packet processing time"
            )

    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped packet processor"""
        return getattr(self.packet_processor, name)

    def process_packet(self, packet):
        """Wrap packet processing with monitoring - SINGLE COUNTER"""
        start_time = time.time()

        try:
            # Get retry handler if available
            retry_handler = self.error_handling.get("packet_retry_handler")

            if retry_handler:
                result = retry_handler.execute(self.packet_processor.process_packet, packet)
            else:
                result = self.packet_processor.process_packet(packet)

            # Increment counter ONCE - this is the single source of truth
            if self.packet_counter:
                self.packet_counter.increment()

            if self.processing_histogram:
                duration = time.time() - start_time
                self.processing_histogram.observe(duration)

            return result

        except Exception as e:
            # Record error but still increment packet counter (packet was processed, just failed)
            if self.packet_counter:
                self.packet_counter.increment()

            if self.error_counter:
                self.error_counter.increment()

            if self.logger:
                self.logger.error(f"Packet processing failed: {e}")

            raise e

    def register_unknown_device(self, device_id: str, name: str, eep_profile: str, **kwargs):
        """Wrap device registration with monitoring"""
        try:
            # Use database circuit breaker if available
            db_circuit_breaker = self.error_handling.get("db_circuit_breaker")

            if db_circuit_breaker:
                result = db_circuit_breaker.call(
                    self.packet_processor.register_unknown_device,
                    device_id, name, eep_profile, **kwargs
                )
            else:
                result = self.packet_processor.register_unknown_device(
                    device_id, name, eep_profile, **kwargs
                )

            # Record device registration event
            if result and self.metrics_collector:
                self.metrics_collector.record_custom_metric(
                    "device_registration_event", 1,
                    tags={"device_id": device_id, "eep_profile": eep_profile}
                )

            return result

        except Exception as e:
            if self.error_counter:
                self.error_counter.increment()
            raise e


def wrap_packet_processor_with_monitoring(packet_processor, metrics_collector=None,
                                          error_handling=None, logger=None):
    """Factory function to wrap existing packet processor with monitoring"""
    if metrics_collector or error_handling:
        return MonitoringWrapper(packet_processor, metrics_collector, error_handling, logger)
    else:
        # No monitoring needed, return original
        return packet_processor

