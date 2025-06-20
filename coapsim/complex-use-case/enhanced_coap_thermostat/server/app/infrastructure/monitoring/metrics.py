
# app/infrastructure/monitoring/metrics.py
"""Performance metrics collection."""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and manages application performance metrics."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.request_times = deque(maxlen=max_history)
        self.error_counts = defaultdict(int)
        self.endpoint_metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "errors": 0
        })
        self.start_time = time.time()
    
    def record_request(self, endpoint: str, duration: float, status_code: int):
        """Record metrics for a request."""
        timestamp = time.time()
        
        # Record request time
        self.request_times.append({
            "timestamp": timestamp,
            "endpoint": endpoint,
            "duration": duration,
            "status_code": status_code
        })
        
        # Update endpoint metrics
        self.endpoint_metrics[endpoint]["count"] += 1
        self.endpoint_metrics[endpoint]["total_time"] += duration
        
        if status_code >= 400:
            self.endpoint_metrics[endpoint]["errors"] += 1
            self.error_counts[status_code] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        now = time.time()
        recent_requests = [
            r for r in self.request_times 
            if now - r["timestamp"] < 300  # Last 5 minutes
        ]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": now - self.start_time,
            "total_requests": len(self.request_times),
            "recent_requests": len(recent_requests),
            "requests_per_minute": len(recent_requests) / 5.0,
            "average_response_time": self._calculate_average_response_time(recent_requests),
            "error_rate": self._calculate_error_rate(recent_requests),
            "endpoint_metrics": dict(self.endpoint_metrics),
            "error_breakdown": dict(self.error_counts)
        }
    
    def _calculate_average_response_time(self, requests: list) -> float:
        """Calculate average response time."""
        if not requests:
            return 0.0
        return sum(r["duration"] for r in requests) / len(requests)
    
    def _calculate_error_rate(self, requests: list) -> float:
        """Calculate error rate as percentage."""
        if not requests:
            return 0.0
        errors = sum(1 for r in requests if r["status_code"] >= 400)
        return (errors / len(requests)) * 100
    
    def get_endpoint_stats(self, endpoint: str) -> Dict[str, Any]:
        """Get statistics for a specific endpoint."""
        metrics = self.endpoint_metrics.get(endpoint, {
            "count": 0,
            "total_time": 0.0,
            "errors": 0
        })
        
        if metrics["count"] > 0:
            avg_time = metrics["total_time"] / metrics["count"]
            error_rate = (metrics["errors"] / metrics["count"]) * 100
        else:
            avg_time = 0.0
            error_rate = 0.0
        
        return {
            "endpoint": endpoint,
            "total_requests": metrics["count"],
            "average_response_time": avg_time,
            "error_rate": error_rate,
            "total_errors": metrics["errors"]
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.request_times.clear()
        self.error_counts.clear()
        self.endpoint_metrics.clear()
        self.start_time = time.time()


# Global metrics collector instance
metrics_collector = MetricsCollector()


def record_request_metrics(endpoint: str, duration: float, status_code: int):
    """Convenience function to record request metrics."""
    metrics_collector.record_request(endpoint, duration, status_code)


def get_current_metrics() -> Dict[str, Any]:
    """Convenience function to get current metrics."""
    return metrics_collector.get_metrics()