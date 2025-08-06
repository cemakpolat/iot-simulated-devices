
# utils/retry_handler.py
import time
import random
from typing import Callable, Type, Tuple, Optional, Any
from dataclasses import dataclass

from enocean_gateway.utils import Logger


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)


class RetryExhaustedException(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


class RetryHandler:
    """Intelligent retry handler with exponential backoff"""

    def __init__(self, config: RetryConfig, logger: Logger):
        self.config = config
        self.logger = logger

    def __call__(self, func: Callable) -> Callable:
        """Decorator to add retry logic to function"""

        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)

        return wrapper

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    self.logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
                return result

            except Exception as e:
                last_exception = e

                # Check if this exception should be retried
                if not any(isinstance(e, exc_type) for exc_type in self.config.retryable_exceptions):
                    self.logger.debug(f"Exception {type(e).__name__} is not retryable")
                    raise e

                # Don't delay on last attempt
                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(
                        f"Attempt {attempt}/{self.config.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"All {self.config.max_attempts} attempts failed for {func.__name__}: {e}"
                    )

        raise RetryExhaustedException(
            f"Function {func.__name__} failed after {self.config.max_attempts} attempts") from last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt using exponential backoff"""
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            # Add random jitter to prevent thundering herd
            jitter = delay * 0.1 * random.random()
            delay += jitter

        return delay