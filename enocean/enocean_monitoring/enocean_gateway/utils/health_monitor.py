# utils/health_monitor.py
import time
import threading
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass

from enocean_gateway.utils import Logger

@dataclass
class HealthCheck:
    """Individual health check configuration"""
    name: str
    check_function: Callable[[], Dict[str, Any]]
    interval: int = 30  # Check interval in seconds
    timeout: int = 10  # Timeout for check in seconds
    critical: bool = False  # Whether failure affects overall health


class HealthMonitor:
    """Comprehensive system health monitoring"""

    def __init__(self, logger: Logger):
        self.logger = logger
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._monitor_thread = None
        self._lock = threading.RLock()

        self._overall_metrics = {
            "start_time": time.time(),
            "total_checks": 0,
            "failed_checks": 0,
            "last_full_check": None,
            "system_healthy": True
        }

    def register_check(self, check: HealthCheck):
        """Register a health check"""
        with self._lock:
            self._checks[check.name] = check
            self._results[check.name] = {
                "status": "unknown",
                "last_check": None,
                "last_success": None,
                "consecutive_failures": 0,
                "total_failures": 0
            }

        self.logger.info(f"Registered health check: {check.name}")

    def start_monitoring(self):
        """Start background health monitoring"""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
        self.logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Stop background health monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("Health monitoring stopped")

    def run_check(self, check_name: str) -> Dict[str, Any]:
        """Run a specific health check immediately"""
        if check_name not in self._checks:
            return {"status": "error", "message": f"Unknown check: {check_name}"}

        check = self._checks[check_name]
        result = self._results[check_name]

        try:
            start_time = time.time()
            check_result = check.check_function()
            duration = time.time() - start_time

            # Update result
            result.update({
                "status": "healthy" if check_result.get("healthy", True) else "unhealthy",
                "last_check": time.time(),
                "duration": duration,
                "details": check_result,
                "consecutive_failures": 0 if check_result.get("healthy", True) else result["consecutive_failures"] + 1
            })

            if check_result.get("healthy", True):
                result["last_success"] = time.time()
            else:
                result["total_failures"] += 1

            self._overall_metrics["total_checks"] += 1

            return result

        except Exception as e:
            # Health check itself failed
            result.update({
                "status": "error",
                "last_check": time.time(),
                "error": str(e),
                "consecutive_failures": result["consecutive_failures"] + 1,
                "total_failures": result["total_failures"] + 1
            })

            self._overall_metrics["total_checks"] += 1
            self._overall_metrics["failed_checks"] += 1

            self.logger.error(f"Health check '{check_name}' failed: {e}")
            return result

    def _monitor_loop(self):
        """Background monitoring loop"""
        last_check_times = {name: 0 for name in self._checks.keys()}

        while self._running:
            try:
                current_time = time.time()

                # Check each registered health check
                for check_name, check in self._checks.items():
                    if current_time - last_check_times[check_name] >= check.interval:
                        self.run_check(check_name)
                        last_check_times[check_name] = current_time

                # Update overall system health
                self._update_overall_health()

                time.sleep(1)  # Check loop every second

            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(5)  # Back off on error

    def _update_overall_health(self):
        """Update overall system health status"""
        system_healthy = True
        critical_failures = []

        for check_name, check in self._checks.items():
            result = self._results[check_name]

            if check.critical and result["status"] != "healthy":
                system_healthy = False
                critical_failures.append(check_name)

        # Update metrics
        self._overall_metrics["system_healthy"] = system_healthy
        self._overall_metrics["last_full_check"] = time.time()

        if critical_failures and system_healthy != self._overall_metrics.get("previous_health", True):
            self.logger.error(f"System health degraded due to critical failures: {critical_failures}")
        elif system_healthy and not self._overall_metrics.get("previous_health", True):
            self.logger.info("System health restored")

        self._overall_metrics["previous_health"] = system_healthy

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        with self._lock:
            return {
                "overall": self._overall_metrics.copy(),
                "checks": {name: result.copy() for name, result in self._results.items()},
                "summary": {
                    "total_checks": len(self._checks),
                    "healthy_checks": sum(1 for r in self._results.values() if r["status"] == "healthy"),
                    "unhealthy_checks": sum(1 for r in self._results.values() if r["status"] == "unhealthy"),
                    "error_checks": sum(1 for r in self._results.values() if r["status"] == "error"),
                    "unknown_checks": sum(1 for r in self._results.values() if r["status"] == "unknown")
                }
            }

    def is_healthy(self) -> bool:
        """Simple health check for external use"""
        return self._overall_metrics["system_healthy"]


