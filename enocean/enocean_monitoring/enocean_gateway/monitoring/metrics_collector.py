# monitoring/metrics_collector.py
from typing import Dict, Any, Optional, List, Union
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time
import threading
from typing import Dict, Any


@dataclass
class MetricPoint:
    """Individual metric data point"""
    name: str
    value: Union[int, float]
    timestamp: float
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class Counter:
    """Thread-safe counter metric"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0
        self._lock = threading.Lock()

    def increment(self, value: Union[int, float] = 1):
        """Increment counter by value"""
        with self._lock:
            self._value += value

    def get_value(self) -> Union[int, float]:
        """Get current counter value"""
        with self._lock:
            return self._value

    def reset(self):
        """Reset counter to zero"""
        with self._lock:
            self._value = 0


class Gauge:
    """Thread-safe gauge metric for values that can go up and down"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0
        self._lock = threading.Lock()

    def set(self, value: Union[int, float]):
        """Set gauge to specific value"""
        with self._lock:
            self._value = value

    def increment(self, value: Union[int, float] = 1):
        """Increment gauge by value"""
        with self._lock:
            self._value += value

    def decrement(self, value: Union[int, float] = 1):
        """Decrement gauge by value"""
        with self._lock:
            self._value -= value

    def get_value(self) -> Union[int, float]:
        """Get current gauge value"""
        with self._lock:
            return self._value


class Histogram:
    """Thread-safe histogram for tracking distributions"""

    def __init__(self, name: str, description: str = "", buckets: List[float] = None):
        self.name = name
        self.description = description
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]

        self._samples = deque(maxlen=10000)  # Keep last 10k samples
        self._bucket_counts = {bucket: 0 for bucket in self.buckets}
        self._bucket_counts['inf'] = 0
        self._lock = threading.Lock()

    def observe(self, value: float):
        """Record a new observation"""
        with self._lock:
            self._samples.append(value)

            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
                    break
            else:
                self._bucket_counts['inf'] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Get histogram statistics"""
        with self._lock:
            if not self._samples:
                return {"count": 0, "mean": 0, "percentiles": {}}

            samples = sorted(self._samples)
            count = len(samples)

            return {
                "count": count,
                "mean": sum(samples) / count,
                "min": samples[0],
                "max": samples[-1],
                "percentiles": {
                    "50": samples[int(count * 0.5)],
                    "90": samples[int(count * 0.9)],
                    "95": samples[int(count * 0.95)],
                    "99": samples[int(count * 0.99)]
                },
                "buckets": self._bucket_counts.copy()
            }


class MetricsCollector:
    """Central metrics collection and management"""

    def __init__(self, logger, storage_path: Optional[str] = None):
        self.logger = logger
        self.storage_path = Path(storage_path) if storage_path else None

        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._custom_metrics: Dict[str, List[MetricPoint]] = defaultdict(list)

        self._lock = threading.RLock()
        self._collection_start = time.time()

        # Built-in system metrics
        self._register_system_metrics()

    def _register_system_metrics(self):
        """Register standard system metrics"""
        # Packet processing metrics
        self.register_counter("packets_processed_total", "Total packets processed")
        self.register_counter("packets_failed_total", "Total packets that failed processing")
        self.register_counter("packets_unknown_total", "Total packets from unknown devices")

        # Device metrics
        self.register_gauge("devices_registered", "Number of registered devices")
        self.register_gauge("devices_unknown", "Number of unknown devices")
        self.register_gauge("devices_active_24h", "Devices active in last 24 hours")

        # System metrics
        self.register_histogram("packet_processing_duration_seconds", "Time to process packets")
        self.register_histogram("discovery_analysis_duration_seconds", "Time to analyze unknown packets")

        # Error metrics
        self.register_counter("errors_total", "Total errors encountered")
        self.register_counter("circuit_breaker_opens_total", "Total circuit breaker opens")

        self.logger.info("Registered system metrics")

    def register_counter(self, name: str, description: str = "") -> Counter:
        """Register a new counter metric"""
        with self._lock:
            if name in self._counters:
                return self._counters[name]

            counter = Counter(name, description)
            self._counters[name] = counter
            self.logger.debug(f"Registered counter metric: {name}")
            return counter

    def register_gauge(self, name: str, description: str = "") -> Gauge:
        """Register a new gauge metric"""
        with self._lock:
            if name in self._gauges:
                return self._gauges[name]

            gauge = Gauge(name, description)
            self._gauges[name] = gauge
            self.logger.debug(f"Registered gauge metric: {name}")
            return gauge

    def register_histogram(self, name: str, description: str = "", buckets: List[float] = None) -> Histogram:
        """Register a new histogram metric"""
        with self._lock:
            if name in self._histograms:
                return self._histograms[name]

            histogram = Histogram(name, description, buckets)
            self._histograms[name] = histogram
            self.logger.debug(f"Registered histogram metric: {name}")
            return histogram

    def get_counter(self, name: str) -> Optional[Counter]:
        """Get counter by name"""
        return self._counters.get(name)

    def get_gauge(self, name: str) -> Optional[Gauge]:
        """Get gauge by name"""
        return self._gauges.get(name)

    def get_histogram(self, name: str) -> Optional[Histogram]:
        """Get histogram by name"""
        return self._histograms.get(name)

    def record_custom_metric(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """Record a custom metric point"""
        with self._lock:
            metric_point = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                tags=tags or {}
            )

            # Keep only last 1000 points per metric
            metrics_list = self._custom_metrics[name]
            metrics_list.append(metric_point)
            if len(metrics_list) > 1000:
                metrics_list.pop(0)

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        with self._lock:
            current_time = time.time()

            metrics = {
                "timestamp": current_time,
                "collection_duration": current_time - self._collection_start,
                "counters": {},
                "gauges": {},
                "histograms": {},
                "custom": {}
            }

            # Collect counter values
            for name, counter in self._counters.items():
                metrics["counters"][name] = {
                    "value": float(counter.get_value()),
                    "description": counter.description
                }

            # Collect gauge values
            for name, gauge in self._gauges.items():
                metrics["gauges"][name] = {
                    "value": float(gauge.get_value()),
                    "description": gauge.description
                }

            # Collect histogram statistics (fix JSON serialization)
            for name, histogram in self._histograms.items():
                stats = histogram.get_statistics()
                # Ensure all values are JSON serializable
                safe_stats = {
                    "count": int(stats.get("count", 0)),
                    "mean": float(stats.get("mean", 0)),
                    "min": float(stats.get("min", 0)) if stats.get("min") is not None else 0,
                    "max": float(stats.get("max", 0)) if stats.get("max") is not None else 0,
                    "percentiles": {
                        k: float(v) for k, v in stats.get("percentiles", {}).items()
                    },
                    "buckets": {
                        str(k): int(v) for k, v in stats.get("buckets", {}).items()
                    }
                }

                metrics["histograms"][name] = {
                    "statistics": safe_stats,
                    "description": histogram.description
                }

            # Collect custom metrics
            for name, points in self._custom_metrics.items():
                if points:
                    latest = points[-1]
                    metrics["custom"][name] = {
                        "latest_value": float(latest.value),
                        "latest_timestamp": float(latest.timestamp),
                        "tags": latest.tags,
                        "point_count": len(points)
                    }

            return metrics

    def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        with self._lock:
            lines = []

            # Export counters
            for name, counter in self._counters.items():
                if counter.description:
                    lines.append(f"# HELP {name} {counter.description}")
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {float(counter.get_value())}")
                lines.append("")

            # Export gauges
            for name, gauge in self._gauges.items():
                if gauge.description:
                    lines.append(f"# HELP {name} {gauge.description}")
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {float(gauge.get_value())}")
                lines.append("")

            # Export histograms
            for name, histogram in self._histograms.items():
                stats = histogram.get_statistics()
                if stats["count"] == 0:
                    continue

                if histogram.description:
                    lines.append(f"# HELP {name} {histogram.description}")
                lines.append(f"# TYPE {name} histogram")

                # Bucket counts (ensure proper sorting and formatting)
                buckets = stats.get("buckets", {})

                # Sort numeric buckets properly
                numeric_buckets = []
                inf_count = 0

                for bucket, count in buckets.items():
                    if bucket == 'inf':
                        inf_count = int(count)
                    else:
                        try:
                            numeric_buckets.append((float(bucket), int(count)))
                        except (ValueError, TypeError):
                            continue

                # Sort by bucket value
                numeric_buckets.sort(key=lambda x: x[0])

                # Output sorted buckets
                for bucket_val, count in numeric_buckets:
                    lines.append(f'{name}_bucket{{le="{bucket_val}"}} {count}')

                # Add +Inf bucket
                lines.append(f'{name}_bucket{{le="+Inf"}} {inf_count}')

                lines.append(f"{name}_count {int(stats['count'])}")
                lines.append(f"{name}_sum {float(stats['mean']) * int(stats['count'])}")
                lines.append("")

            return "\n".join(lines)

    def save_to_storage(self):
        """Save current metrics to storage"""
        if not self.storage_path:
            return

        try:
            metrics_data = self.get_all_metrics()

            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(metrics_data, f, indent=2)

            self.logger.debug(f"Saved metrics to {self.storage_path}")

        except Exception as e:
            self.logger.error(f"Failed to save metrics to storage: {e}")

    def reset_all_counters(self):
        """Reset all counters to zero"""
        with self._lock:
            for counter in self._counters.values():
                counter.reset()

            self.logger.info("Reset all counter metrics")

    def get_summary(self) -> Dict[str, Any]:
        """Get high-level metrics summary"""
        with self._lock:
            return {
                "total_counters": len(self._counters),
                "total_gauges": len(self._gauges),
                "total_histograms": len(self._histograms),
                "total_custom_metrics": len(self._custom_metrics),
                "collection_uptime": time.time() - self._collection_start,
                "key_metrics": {
                    "packets_processed": self._counters.get("packets_processed_total", Counter("", "")).get_value(),
                    "devices_registered": self._gauges.get("devices_registered", Gauge("", "")).get_value(),
                    "errors_total": self._counters.get("errors_total", Counter("", "")).get_value()
                }
            }
