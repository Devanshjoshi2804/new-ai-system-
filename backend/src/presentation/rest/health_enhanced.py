"""
Enhanced health check endpoint with comprehensive system monitoring
"""
from fastapi import APIRouter
from typing import Dict, Any
import logging

from src.infrastructure.monitoring.performance_monitor import get_monitor, get_health_checker
from src.infrastructure.ai.cache.ai_cache import get_cache
from src.infrastructure.ai.resilience.circuit_breaker import get_circuit_breaker_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint
    
    Returns:
        System health status including:
        - Overall health status
        - AI provider availability
        - Cache statistics
        - Circuit breaker states
        - Performance metrics
    """
    try:
        health_checker = get_health_checker()
        
        # Register health checks
        health_checker.register_check("cache", check_cache_health)
        health_checker.register_check("circuit_breakers", check_circuit_breakers)
        health_checker.register_check("performance", check_performance)
        
        # Run all checks
        health_status = await health_checker.check_health()
        
        return {
            "status": "healthy" if health_status['healthy'] else "unhealthy",
            "service": "AI Integration Platform - Production Ready",
            "version": "2.0.0",
            "timestamp": health_status['timestamp'],
            "checks": health_status['checks']
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Health check error: {e}")
        return {
            "status": "error",
            "service": "AI Integration Platform",
            "error": str(e)
        }


async def check_cache_health() -> Dict[str, Any]:
    """Check cache health"""
    try:
        cache = get_cache()
        stats = await cache.get_stats()
        
        return {
            'healthy': True,
            'memory_items': stats.get('memory_items', 0),
            'disk_items': stats.get('disk_items', 0),
            'ttl': stats.get('ttl', 0)
        }
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


async def check_circuit_breakers() -> Dict[str, Any]:
    """Check circuit breaker states"""
    try:
        manager = get_circuit_breaker_manager()
        states = manager.get_all_states()
        
        all_closed = all(
            state['state'] == 'closed'
            for state in states.values()
        ) if states else True
        
        return {
            'healthy': all_closed,
            'breakers': states
        }
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


async def check_performance() -> Dict[str, Any]:
    """Check performance metrics"""
    try:
        monitor = get_monitor()
        stats = await monitor.get_stats()
        
        # Check if any operation has low success rate
        low_success_rate = any(
            metric_stats.get('success_rate', 100) < 70
            for metric_stats in stats.values()
            if isinstance(metric_stats, dict)
        )
        
        return {
            'healthy': not low_success_rate,
            'metrics': stats
        }
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


@router.get("/health/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get detailed performance metrics
    
    Returns:
        Detailed performance statistics
    """
    try:
        monitor = get_monitor()
        stats = await monitor.get_stats()
        
        return {
            "success": True,
            "metrics": stats
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error getting metrics: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/health/cache")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics
    
    Returns:
        Cache statistics
    """
    try:
        cache = get_cache()
        stats = await cache.get_stats()
        
        return {
            "success": True,
            "cache": stats
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error getting cache stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/health/cache/clear")
async def clear_cache() -> Dict[str, Any]:
    """
    Clear AI response cache
    
    Returns:
        Success status
    """
    try:
        cache = get_cache()
        await cache.clear()
        
        return {
            "success": True,
            "message": "Cache cleared successfully"
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error clearing cache: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/health/circuit-breakers")
async def get_circuit_breaker_states() -> Dict[str, Any]:
    """
    Get circuit breaker states
    
    Returns:
        Circuit breaker states
    """
    try:
        manager = get_circuit_breaker_manager()
        states = manager.get_all_states()
        
        return {
            "success": True,
            "circuit_breakers": states
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error getting circuit breaker states: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/health/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(name: str) -> Dict[str, Any]:
    """
    Reset a circuit breaker
    
    Args:
        name: Circuit breaker name
        
    Returns:
        Success status
    """
    try:
        manager = get_circuit_breaker_manager()
        await manager.reset(name)
        
        return {
            "success": True,
            "message": f"Circuit breaker '{name}' reset successfully"
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Error resetting circuit breaker: {e}")
        return {
            "success": False,
            "error": str(e)
        }

