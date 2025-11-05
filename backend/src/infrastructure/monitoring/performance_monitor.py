"""
Performance Monitoring System
Track response times, success rates, and system health
"""
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance metric"""
    name: str
    duration: float
    success: bool
    timestamp: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Monitor and track system performance
    
    Features:
    - Response time tracking
    - Success/failure rates
    - Percentile calculations (p50, p95, p99)
    - Real-time statistics
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize performance monitor
        
        Args:
            max_history: Maximum metrics to keep in memory
        """
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = asyncio.Lock()
        
        logger.info(f"[INFO] Performance monitor initialized (max_history={max_history})")
    
    async def record(
        self,
        name: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
        **metadata
    ):
        """
        Record a performance metric
        
        Args:
            name: Metric name (e.g., "api_analysis", "pdf_parsing")
            duration: Duration in seconds
            success: Whether operation succeeded
            error: Error message if failed
            **metadata: Additional metadata
        """
        metric = PerformanceMetric(
            name=name,
            duration=duration,
            success=success,
            timestamp=time.time(),
            error=error,
            metadata=metadata
        )
        
        async with self._lock:
            self.metrics[name].append(metric)
        
        # Log slow operations
        if duration > 30:
            logger.warning(f"[WARN] Slow operation: {name} took {duration:.2f}s")
        
        # Log failures
        if not success:
            logger.error(f"[ERROR] Operation failed: {name} - {error}")
    
    async def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics
        
        Args:
            name: Specific metric name, or None for all
            
        Returns:
            Statistics dictionary
        """
        async with self._lock:
            if name:
                return await self._calculate_stats(name)
            else:
                return {
                    metric_name: await self._calculate_stats(metric_name)
                    for metric_name in self.metrics.keys()
                }
    
    async def _calculate_stats(self, name: str) -> Dict[str, Any]:
        """Calculate statistics for a metric"""
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return {
                'count': 0,
                'success_rate': 0.0,
                'avg_duration': 0.0,
                'min_duration': 0.0,
                'max_duration': 0.0,
                'p50': 0.0,
                'p95': 0.0,
                'p99': 0.0
            }
        
        metrics_list = list(self.metrics[name])
        
        # Calculate success rate
        total = len(metrics_list)
        successes = sum(1 for m in metrics_list if m.success)
        success_rate = (successes / total) * 100 if total > 0 else 0
        
        # Calculate duration statistics
        durations = [m.duration for m in metrics_list]
        durations.sort()
        
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        # Calculate percentiles
        p50 = durations[int(len(durations) * 0.50)] if durations else 0
        p95 = durations[int(len(durations) * 0.95)] if durations else 0
        p99 = durations[int(len(durations) * 0.99)] if durations else 0
        
        # Recent metrics (last 10)
        recent = metrics_list[-10:]
        recent_success_rate = (sum(1 for m in recent if m.success) / len(recent)) * 100
        
        return {
            'count': total,
            'success_count': successes,
            'failure_count': total - successes,
            'success_rate': round(success_rate, 2),
            'recent_success_rate': round(recent_success_rate, 2),
            'avg_duration': round(avg_duration, 2),
            'min_duration': round(min_duration, 2),
            'max_duration': round(max_duration, 2),
            'p50': round(p50, 2),
            'p95': round(p95, 2),
            'p99': round(p99, 2),
            'last_error': next((m.error for m in reversed(metrics_list) if m.error), None)
        }
    
    async def clear(self, name: Optional[str] = None):
        """Clear metrics"""
        async with self._lock:
            if name:
                if name in self.metrics:
                    self.metrics[name].clear()
            else:
                self.metrics.clear()
        
        logger.info(f"[DEL] Cleared metrics: {name or 'all'}")


# Global monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get or create global monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


class PerformanceTracker:
    """Context manager for tracking operation performance"""
    
    def __init__(self, name: str, **metadata):
        """
        Initialize performance tracker
        
        Args:
            name: Operation name
            **metadata: Additional metadata
        """
        self.name = name
        self.metadata = metadata
        self.start_time = None
        self.monitor = get_monitor()
    
    async def __aenter__(self):
        """Start tracking"""
        self.start_time = time.time()
        logger.debug(f"⏱[INFO] Started tracking: {self.name}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking and record metric"""
        duration = time.time() - self.start_time
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        
        await self.monitor.record(
            name=self.name,
            duration=duration,
            success=success,
            error=error,
            **self.metadata
        )
        
        if success:
            logger.debug(f"[OK] Completed: {self.name} ({duration:.2f}s)")
        else:
            logger.error(f"[ERROR] Failed: {self.name} ({duration:.2f}s) - {error}")
        
        return False  # Don't suppress exceptions


def track_performance(name: str, **metadata):
    """
    Decorator for tracking function performance
    
    Usage:
        @track_performance("api_analysis")
        async def analyze_api():
            # ... code ...
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with PerformanceTracker(name, **metadata):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


class HealthChecker:
    """
    System health checker
    
    Checks:
    - AI provider availability
    - Cache health
    - Circuit breaker states
    - Performance metrics
    """
    
    def __init__(self):
        """Initialize health checker"""
        self.checks: Dict[str, callable] = {}
    
    def register_check(self, name: str, check_func: callable):
        """Register a health check"""
        self.checks[name] = check_func
        logger.info(f"[OK] Registered health check: {name}")
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Run all health checks
        
        Returns:
            Health status dictionary
        """
        results = {
            'healthy': True,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        for name, check_func in self.checks.items():
            try:
                check_result = await check_func()
                results['checks'][name] = {
                    'status': 'healthy' if check_result else 'unhealthy',
                    'details': check_result
                }
                
                if not check_result:
                    results['healthy'] = False
            
            except Exception as e:
                logger.error(f"[ERROR] Health check failed: {name} - {e}")
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(e)
                }
                results['healthy'] = False
        
        return results


# Global health checker
_global_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker"""
    global _global_health_checker
    if _global_health_checker is None:
        _global_health_checker = HealthChecker()
    return _global_health_checker

