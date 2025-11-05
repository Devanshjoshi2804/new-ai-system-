"""
Retry Handler with Exponential Backoff
Handles transient failures gracefully
"""
import asyncio
import logging
from typing import Optional, Callable, Any, TypeVar
from functools import wraps
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    retry_on: Optional[tuple] = None,
    **kwargs
) -> Any:
    """
    Execute function with exponential backoff retry
    
    Args:
        func: Async function to execute
        *args: Function arguments
        config: Retry configuration
        retry_on: Tuple of exceptions to retry on
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()
    
    if retry_on is None:
        retry_on = (Exception,)
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"[INFO] Retry attempt {attempt}/{config.max_retries}")
            
            result = await func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"[OK] Retry successful on attempt {attempt}")
            
            return result
        
        except retry_on as e:
            last_exception = e
            
            if attempt == config.max_retries:
                logger.error(f"[ERROR] All {config.max_retries} retry attempts failed")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(
                config.initial_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            
            # Add jitter if enabled
            if config.jitter:
                import random
                delay = delay * (0.5 + random.random())
            
            # Check if it's a rate limit error
            error_msg = str(e).lower()
            is_rate_limit = any(
                keyword in error_msg
                for keyword in ['429', 'rate', 'limit', 'capacity', 'exceeded', 'quota']
            )
            
            if is_rate_limit:
                # Use longer delay for rate limits
                delay = min(delay * 2, config.max_delay)
                logger.warning(f"[WARN] Rate limit detected, waiting {delay:.1f}s before retry...")
            else:
                logger.warning(f"[WARN] Error: {e}, retrying in {delay:.1f}s...")
            
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    raise Exception("Retry failed for unknown reason")


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: Optional[tuple] = None
):
    """
    Decorator for automatic retry with exponential backoff
    
    Usage:
        @with_retry(max_retries=3, initial_delay=1.0)
        async def my_function():
            # ... code that might fail ...
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay
            )
            return await retry_with_backoff(
                func,
                *args,
                config=config,
                retry_on=retry_on or (Exception,),
                **kwargs
            )
        return wrapper
    return decorator


class RateLimiter:
    """
    Rate limiter to prevent overwhelming APIs
    """
    
    def __init__(
        self,
        max_calls: int,
        time_window: float
    ):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: list[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until rate limit allows another call"""
        async with self._lock:
            now = time.time()
            
            # Remove old calls outside time window
            self.calls = [
                call_time for call_time in self.calls
                if now - call_time < self.time_window
            ]
            
            # Check if we're at limit
            if len(self.calls) >= self.max_calls:
                # Calculate wait time
                oldest_call = self.calls[0]
                wait_time = self.time_window - (now - oldest_call)
                
                if wait_time > 0:
                    logger.debug(f"⏳ Rate limit reached, waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    
                    # Retry acquire after waiting
                    return await self.acquire()
            
            # Record this call
            self.calls.append(now)
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass


class TimeoutHandler:
    """
    Timeout handler for long-running operations
    """
    
    @staticmethod
    async def with_timeout(
        func: Callable[..., Any],
        timeout: float,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with timeout
        
        Args:
            func: Async function to execute
            timeout: Timeout in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            asyncio.TimeoutError if timeout exceeded
        """
        try:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"[ERROR] Operation timed out after {timeout}s")
            raise
    
    @staticmethod
    def with_timeout_decorator(timeout: float):
        """
        Decorator for automatic timeout
        
        Usage:
            @with_timeout_decorator(30.0)
            async def my_function():
                # ... long-running code ...
                pass
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await TimeoutHandler.with_timeout(
                    func,
                    timeout,
                    *args,
                    **kwargs
                )
            return wrapper
        return decorator


# Convenience decorators combining retry and timeout
def resilient_call(
    max_retries: int = 3,
    timeout: float = 30.0,
    initial_delay: float = 1.0
):
    """
    Decorator combining retry and timeout for resilient API calls
    
    Usage:
        @resilient_call(max_retries=3, timeout=30.0)
        async def call_external_api():
            # ... API call code ...
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                initial_delay=initial_delay
            )
            
            async def timed_func():
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            
            return await retry_with_backoff(
                timed_func,
                config=config
            )
        return wrapper
    return decorator

