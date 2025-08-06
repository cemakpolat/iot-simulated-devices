# utils/circuit_breaker.py
import time
import threading
from enum import Enum
from typing import Callable, Optional, Any, Dict
from dataclasses import dataclass
from ..utils.logger import Logger

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, calls are failing
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    timeout: int = 60  # Seconds to wait before trying again
    success_threshold: int = 3  # Successes needed to close circuit
    expected_exception: type = Exception  # Exception type that triggers circuit


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance"""

    def __init__(self, config: CircuitBreakerConfig, logger: Logger, name: str = "CircuitBreaker"):
        self.config = config
        self.logger = logger
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._lock = threading.RLock()

        self._metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_opens": 0,
            "circuit_closes": 0
        }

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker"""

        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self._lock:
            self._metrics["total_calls"] += 1

            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self.logger.info(f"{self.name}: Circuit moved to HALF_OPEN")
                else:
                    self._metrics["failed_calls"] += 1
                    raise CircuitBreakerOpenException(f"Circuit breaker {self.name} is OPEN")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result

            except self.config.expected_exception as e:
                self._on_failure()
                raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self._last_failure_time is None:
            return True

        return time.time() - self._last_failure_time >= self.config.timeout

    def _on_success(self):
        """Handle successful call"""
        self._metrics["successful_calls"] += 1

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._reset()
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0  # Reset failure count on success

    def _on_failure(self):
        """Handle failed call"""
        self._metrics["failed_calls"] += 1
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._trip()
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._trip()

    def _trip(self):
        """Trip the circuit breaker (open it)"""
        self._state = CircuitState.OPEN
        self._success_count = 0
        self._metrics["circuit_opens"] += 1
        self.logger.warning(f"{self.name}: Circuit breaker OPENED after {self._failure_count} failures")

    def _reset(self):
        """Reset the circuit breaker (close it)"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._metrics["circuit_closes"] += 1
        self.logger.info(f"{self.name}: Circuit breaker CLOSED")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    @property
    def metrics(self) -> Dict[str, int]:
        """Get circuit breaker metrics"""
        return self._metrics.copy()

    def force_open(self):
        """Manually open the circuit"""
        with self._lock:
            self._trip()

    def force_close(self):
        """Manually close the circuit"""
        with self._lock:
            self._reset()




