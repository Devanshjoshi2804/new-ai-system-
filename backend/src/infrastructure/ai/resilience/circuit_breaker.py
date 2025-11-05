"""
Circuit Breaker Pattern
Prevents cascading failures by stopping calls to failing services
"""
import asyncio
import logging
import time
from typing import Optional, Callable, Any
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures
    
    States:
    - CLOSED: Normal operation, all calls go through
    - OPEN: Too many failures, reject all calls immediately
    - HALF_OPEN: Testing if service recovered, allow limited calls
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes in half-open to close circuit
            timeout: Time to wait before trying half-open (seconds)
            name: Name for logging
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name or "unnamed"
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
        
        logger.info(
            f"[INFO] Circuit breaker '{self.name}' initialized: "
            f"failure_threshold={failure_threshold}, timeout={timeout}s"
        )
    
    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError if circuit is open
        """
        async with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self.state == CircuitState.OPEN:
                if self.last_failure_time and \
                   time.time() - self.last_failure_time >= self.timeout:
                    logger.info(f"[INFO] Circuit '{self.name}' transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    # Circuit is still open, reject call
                    logger.warning(
                        f"[WARN] Circuit '{self.name}' is OPEN, rejecting call "
                        f"(will retry in {self.timeout - (time.time() - self.last_failure_time):.1f}s)"
                    )
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is open"
                    )
        
        # Execute the function
        try:
            result = await func(*args, **kwargs)
            
            # Success! Update state
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    self.success_count += 1
                    logger.debug(
                        f"[OK] Circuit '{self.name}' success in HALF_OPEN "
                        f"({self.success_count}/{self.success_threshold})"
                    )
                    
                    if self.success_count >= self.success_threshold:
                        logger.info(f"[INFO] Circuit '{self.name}' closing (service recovered)")
                        self.state = CircuitState.CLOSED
                        self.failure_count = 0
                        self.success_count = 0
                
                elif self.state == CircuitState.CLOSED:
                    # Reset failure count on success
                    self.failure_count = 0
            
            return result
        
        except Exception as e:
            # Failure! Update state
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.state == CircuitState.HALF_OPEN:
                    # Failed in half-open, go back to open
                    logger.warning(
                        f"[WARN] Circuit '{self.name}' failed in HALF_OPEN, "
                        f"reopening circuit"
                    )
                    self.state = CircuitState.OPEN
                    self.success_count = 0
                
                elif self.state == CircuitState.CLOSED:
                    logger.warning(
                        f"[WARN] Circuit '{self.name}' failure "
                        f"({self.failure_count}/{self.failure_threshold})"
                    )
                    
                    if self.failure_count >= self.failure_threshold:
                        logger.error(
                            f"[ERROR] Circuit '{self.name}' opening due to "
                            f"{self.failure_count} failures"
                        )
                        self.state = CircuitState.OPEN
            
            raise
    
    async def reset(self):
        """Manually reset circuit breaker"""
        async with self._lock:
            logger.info(f"[INFO] Circuit '{self.name}' manually reset")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'failure_threshold': self.failure_threshold,
            'success_threshold': self.success_threshold,
            'timeout': self.timeout,
            'last_failure_time': self.last_failure_time
        }


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers
    """
    
    def __init__(self):
        """Initialize circuit breaker manager"""
        self.breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            timeout: Time to wait before half-open
            
        Returns:
            Circuit breaker instance
        """
        async with self._lock:
            if name not in self.breakers:
                self.breakers[name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    timeout=timeout,
                    name=name
                )
            return self.breakers[name]
    
    async def call(
        self,
        name: str,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function through named circuit breaker
        
        Args:
            name: Circuit breaker name
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        breaker = await self.get_breaker(name)
        return await breaker.call(func, *args, **kwargs)
    
    async def reset(self, name: str):
        """Reset named circuit breaker"""
        if name in self.breakers:
            await self.breakers[name].reset()
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            await breaker.reset()
    
    def get_all_states(self) -> dict[str, dict]:
        """Get states of all circuit breakers"""
        return {
            name: breaker.get_state()
            for name, breaker in self.breakers.items()
        }


# Global circuit breaker manager
_global_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get or create global circuit breaker manager"""
    global _global_manager
    if _global_manager is None:
        _global_manager = CircuitBreakerManager()
    return _global_manager


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout: float = 60.0
):
    """
    Decorator for automatic circuit breaker protection
    
    Usage:
        @with_circuit_breaker("external_api", failure_threshold=5)
        async def call_external_api():
            # ... API call code ...
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            breaker = await manager.get_breaker(
                name,
                failure_threshold=failure_threshold,
                timeout=timeout
            )
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator

