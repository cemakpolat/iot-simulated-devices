
# monitoring/performance_monitor.py
import psutil
import time
import threading
from typing import Dict, Any

from enocean_gateway.monitoring.metrics_collector import MetricsCollector


class PerformanceMonitor:
    """Monitor system performance metrics"""

    def __init__(self, logger, metrics_collector: MetricsCollector):
        self.logger = logger
        self.metrics = metrics_collector
        self._process = psutil.Process()
        self._monitoring = False
        self._monitor_thread = None

    def start_monitoring(self, interval: int = 30):
        """Start performance monitoring"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        self.logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("Performance monitoring stopped")

    def _monitor_loop(self, interval: int):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                self._collect_system_metrics()
                self._collect_process_metrics()
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")
                time.sleep(interval)

    def _collect_system_metrics(self):
        """Collect system-wide performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.record_custom_metric("system_cpu_percent", cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics.record_custom_metric("system_memory_percent", memory.percent)
            self.metrics.record_custom_metric("system_memory_available_bytes", memory.available)

            # Disk usage
            disk = psutil.disk_usage('/')
            self.metrics.record_custom_metric("system_disk_percent", (disk.used / disk.total) * 100)
            self.metrics.record_custom_metric("system_disk_free_bytes", disk.free)

            # Network I/O
            net_io = psutil.net_io_counters()
            self.metrics.record_custom_metric("system_network_bytes_sent", net_io.bytes_sent)
            self.metrics.record_custom_metric("system_network_bytes_recv", net_io.bytes_recv)

        except Exception as e:
            self.logger.warning(f"Failed to collect system metrics: {e}")

    def _collect_process_metrics(self):
        """Collect process-specific performance metrics"""
        try:
            # Process CPU and memory
            cpu_percent = self._process.cpu_percent()
            memory_info = self._process.memory_info()

            self.metrics.record_custom_metric("process_cpu_percent", cpu_percent)
            self.metrics.record_custom_metric("process_memory_bytes", memory_info.rss)
            self.metrics.record_custom_metric("process_memory_percent", self._process.memory_percent())

            # Process I/O
            try:
                io_counters = self._process.io_counters()
                self.metrics.record_custom_metric("process_io_read_bytes", io_counters.read_bytes)
                self.metrics.record_custom_metric("process_io_write_bytes", io_counters.write_bytes)
            except AttributeError:
                # I/O counters not available on all platforms
                pass

            # Thread count
            self.metrics.record_custom_metric("process_threads", self._process.num_threads())

            # File descriptors (Unix-like systems)
            try:
                self.metrics.record_custom_metric("process_open_files", self._process.num_fds())
            except AttributeError:
                # num_fds() not available on Windows
                pass

        except psutil.NoSuchProcess:
            self.logger.warning("Process no longer exists")
        except Exception as e:
            self.logger.warning(f"Failed to collect process metrics: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        try:
            return {
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
                },
                "process": {
                    "cpu_percent": self._process.cpu_percent(),
                    "memory_bytes": self._process.memory_info().rss,
                    "memory_percent": self._process.memory_percent(),
                    "threads": self._process.num_threads()
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get performance summary: {e}")
            return {"error": str(e)}

