# utils/enhanced_error_handling.py
from typing import Dict, Any, Callable, Optional
from enocean_gateway.utils.dead_letter_queue import DeadLetterQueue, DeadLetterMessage
from enocean_gateway.utils.retry_handler import RetryHandler, RetryExhaustedException
from enocean_gateway.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from enocean_gateway.utils.logger import Logger


class EnhancedErrorHandling:
    """Unified error handling that integrates DLQ with existing components"""
    
    def __init__(self, 
                 retry_handler: RetryHandler,
                 circuit_breaker: CircuitBreaker,
                 dlq: DeadLetterQueue,
                 logger: Logger,
                 name: str = ""):
        self.retry_handler = retry_handler
        self.circuit_breaker = circuit_breaker
        self.dlq = dlq
        self.logger = logger
        self.name = name
        
        # Start DLQ processor with retry function
        self.dlq.start_processor(self._retry_dlq_message)
    
    def execute_with_full_error_handling(self, 
                                       func: Callable, 
                                       function_name: str,
                                       *args, **kwargs) -> Any:
        """Execute function with complete error handling chain"""
        try:
            # Step 1: Try with circuit breaker protection
            return self.circuit_breaker.call(
                lambda: self.retry_handler.execute(func, *args, **kwargs)
            )
            
        except CircuitBreakerOpenException as e:
            # Circuit breaker is open - add to DLQ immediately
            self.logger.error(f"Circuit breaker open for {function_name}, adding to DLQ")
            self.dlq.add_message(function_name, args, kwargs, e, max_retries=5)
            raise
            
        except RetryExhaustedException as e:
            # All retries failed - add to DLQ
            self.logger.error(f"All retries exhausted for {function_name}, adding to DLQ")
            self.dlq.add_message(function_name, args, kwargs, e, max_retries=3)
            raise
            
        except Exception as e:
            # Unexpected error - add to DLQ
            self.logger.error(f"Unexpected error in {function_name}, adding to DLQ")
            self.dlq.add_message(function_name, args, kwargs, e, max_retries=2)
            raise
    
    def _retry_dlq_message(self, message: DeadLetterMessage) -> bool:
        """Retry function for DLQ processor"""
        try:
            self.logger.info(f"Attempting to retry DLQ message {message.id} for {message.original_function}")
            
            # For now, we'll log and return False - this can be enhanced later
            # with specific retry logic for different function types
            self.logger.warning(f"DLQ retry not yet implemented for {message.original_function}")
            return False
            
        except Exception as e:
            self.logger.warning(f"DLQ retry failed for {message.id}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error handling statistics"""
        dlq_stats = self.dlq.get_statistics()
        
        # Add circuit breaker stats if available
        cb_stats = {}
        if hasattr(self.circuit_breaker, 'metrics'):
            cb_stats = self.circuit_breaker.metrics
        
        return {
            "name": self.name,
            "dead_letter_queue": dlq_stats,
            "circuit_breaker": cb_stats,
            "retry_handler": {
                "max_attempts": self.retry_handler.config.max_attempts,
                "base_delay": self.retry_handler.config.base_delay
            }
        }
    
    def get_dlq_messages(self) -> list:
        """Get current DLQ messages for inspection"""
        return self.dlq.get_messages()
    
    def stop(self):
        """Stop the DLQ processor"""
        self.dlq.stop_processor()


class ErrorHandlingFactory:
    """Factory for creating error handling components"""
    
    @staticmethod
    def create_enhanced_error_handling(settings, logger: Logger) -> Dict[str, Any]:
        """Create enhanced error handling components with DLQ"""
        from enocean_gateway.utils.circuit_breaker import CircuitBreakerConfig
        from enocean_gateway.utils.retry_handler import RetryConfig
        
        # Serial connection components
        serial_circuit_config = CircuitBreakerConfig(
            failure_threshold=getattr(settings, 'SERIAL_FAILURE_THRESHOLD', 3),
            timeout=getattr(settings, 'SERIAL_TIMEOUT', 30),
            success_threshold=2,
            expected_exception=(OSError, TimeoutError)
        )
        serial_circuit_breaker = CircuitBreaker(serial_circuit_config, logger, "SerialConnection")
        
        # Database components
        db_circuit_config = CircuitBreakerConfig(
            failure_threshold=getattr(settings, 'DB_FAILURE_THRESHOLD', 5),
            timeout=getattr(settings, 'DB_TIMEOUT', 60),
            success_threshold=3,
            expected_exception=(Exception,)
        )
        db_circuit_breaker = CircuitBreaker(db_circuit_config, logger, "DatabaseOperations")
        
        # Retry handler for packets
        packet_retry_config = RetryConfig(
            max_attempts=getattr(settings, 'PACKET_RETRY_ATTEMPTS', 3),
            base_delay=0.1,
            max_delay=2.0,
            retryable_exceptions=(ValueError, KeyError, AttributeError)
        )
        packet_retry_handler = RetryHandler(packet_retry_config, logger)
        
        # Retry handler for database operations
        db_retry_config = RetryConfig(
            max_attempts=getattr(settings, 'DB_RETRY_ATTEMPTS', 3),
            base_delay=0.5,
            max_delay=5.0,
            retryable_exceptions=(Exception,)
        )
        db_retry_handler = RetryHandler(db_retry_config, logger)
        
        # Dead Letter Queues (separate for different types of operations)
        dlq_storage_path = getattr(settings, 'DLQ_STORAGE_PATH', 'data/dead_letter_queue.json')
        dlq_max_size = getattr(settings, 'DLQ_MAX_SIZE', 1000)
        
        serial_dlq = DeadLetterQueue(
            dlq_storage_path.replace('.json', '_serial.json'), 
            logger, 
            dlq_max_size
        )
        db_dlq = DeadLetterQueue(
            dlq_storage_path.replace('.json', '_database.json'), 
            logger, 
            dlq_max_size
        )
        
        # Enhanced error handling instances
        serial_error_handler = EnhancedErrorHandling(
            packet_retry_handler, serial_circuit_breaker, serial_dlq, logger, "serial"
        )
        
        db_error_handler = EnhancedErrorHandling(
            db_retry_handler, db_circuit_breaker, db_dlq, logger, "database"
        )
        
        return {
            # Enhanced handlers
            "serial": serial_error_handler,
            "database": db_error_handler,
            
            # Individual DLQs for direct access
            "serial_dlq": serial_dlq,
            "database_dlq": db_dlq,
            
            # Keep original components for backward compatibility
            "serial_circuit_breaker": serial_circuit_breaker,
            "db_circuit_breaker": db_circuit_breaker,
            "packet_retry_handler": packet_retry_handler,
            "db_retry_handler": db_retry_handler
        }