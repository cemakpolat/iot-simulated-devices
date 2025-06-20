# app/utils/decorators.py
"""Custom decorators for the application."""

import functools
import logging
import time
from typing import Callable, Any
from datetime import datetime

from ..core.exceptions import ValidationError, AuthenticationError

logger = logging.getLogger(__name__)


def log_execution_time(func: Callable) -> Callable:
    """Decorator to log function execution time."""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
    
    # Return appropriate wrapper based on function type
    if hasattr(func, '__code__') and 'await' in func.__code__.co_names:
        return async_wrapper
    else:
        return sync_wrapper


def validate_input(**validation_rules):
    """Decorator to validate function inputs."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Validate arguments based on rules
            for param_name, rule in validation_rules.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    
                    if rule == 'required' and value is None:
                        raise ValidationError(f"Parameter '{param_name}' is required")
                    
                    elif rule == 'positive_int' and (not isinstance(value, int) or value <= 0):
                        raise ValidationError(f"Parameter '{param_name}' must be a positive integer")
                    
                    elif rule == 'non_empty_string' and (not isinstance(value, str) or not value.strip()):
                        raise ValidationError(f"Parameter '{param_name}' must be a non-empty string")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def cache_result(ttl_seconds: int = 300):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Check if result is in cache and not expired
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            
            # Clean up expired cache entries
            current_time = time.time()
            expired_keys = [k for k, (_, ts) in cache.items() if current_time - ts >= ttl_seconds]
            for key in expired_keys:
                del cache[key]
            
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl_seconds:
                    return result
            
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            
            # Clean up expired entries
            current_time = time.time()
            expired_keys = [k for k, (_, ts) in cache.items() if current_time - ts >= ttl_seconds]
            for key in expired_keys:
                del cache[key]
            
            return result
        
        # Return appropriate wrapper
        if hasattr(func, '__code__') and 'await' in func.__code__.co_names:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def require_permissions(*required_permissions):
    """Decorator to require specific permissions for endpoint access."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract user from kwargs (assumes user is passed as current_user)
            user = None
            for key, value in kwargs.items():
                if hasattr(value, 'roles'):
                    user = value
                    break
            
            if not user:
                raise AuthenticationError("User authentication required")
            
            user_roles = getattr(user, 'roles', [])
            
            # Check if user has required permissions
            if required_permissions and not any(perm in user_roles for perm in required_permissions):
                raise AuthenticationError(f"Insufficient permissions. Required: {required_permissions}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(max_calls: int = 100, window_seconds: int = 3600):
    """Decorator for basic rate limiting."""
    def decorator(func: Callable) -> Callable:
        call_history = {}
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Simple rate limiting based on function calls
            # In production, this would use Redis or similar
            current_time = time.time()
            
            # Clean up old entries
            cutoff_time = current_time - window_seconds
            call_history.clear()  # Simplified cleanup
            
            # Count recent calls
            recent_calls = len([t for t in call_history.values() if t > cutoff_time])
            
            if recent_calls >= max_calls:
                raise ValidationError(f"Rate limit exceeded: {max_calls} calls per {window_seconds} seconds")
            
            # Record this call
            call_key = f"{current_time}:{id(args)}"
            call_history[call_key] = current_time
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator