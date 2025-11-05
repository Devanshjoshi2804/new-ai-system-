"""
AI Response Cache - Avoid redundant AI calls
Massive speed improvement by caching AI responses
"""
import hashlib
import json
import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class AIResponseCache:
    """
    Cache AI responses to avoid redundant calls
    
    Features:
    - In-memory cache with TTL
    - Persistent disk cache for long-term storage
    - Automatic cache invalidation
    - Thread-safe operations
    """
    
    def __init__(
        self,
        ttl: int = 3600,  # 1 hour default
        max_memory_items: int = 1000,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize AI cache
        
        Args:
            ttl: Time-to-live in seconds
            max_memory_items: Maximum items in memory cache
            cache_dir: Directory for persistent cache
        """
        self.ttl = ttl
        self.max_memory_items = max_memory_items
        self.memory_cache: Dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        
        # Setup persistent cache
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = Path("/tmp/ai_cache")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[OK] AI Cache initialized: TTL={ttl}s, max_items={max_memory_items}, cache_dir={self.cache_dir}")
    
    def _generate_key(self, prompt: str, model: str, **kwargs) -> str:
        """Generate cache key from prompt and parameters"""
        # Include all relevant parameters in key
        key_data = {
            "prompt": prompt,
            "model": model,
            **kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def get(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> Optional[str]:
        """
        Get cached response
        
        Args:
            prompt: The prompt text
            model: Model name
            **kwargs: Additional parameters (temperature, etc.)
            
        Returns:
            Cached response or None
        """
        try:
            key = self._generate_key(prompt, model, **kwargs)
            
            # Check memory cache first
            async with self._lock:
                if key in self.memory_cache:
                    response, timestamp = self.memory_cache[key]
                    if time.time() - timestamp < self.ttl:
                        logger.info(f"[OK] Cache HIT (memory): {key[:16]}...")
                        return response
                    else:
                        # Expired, remove from cache
                        del self.memory_cache[key]
                        logger.debug(f"[DEL] Cache expired: {key[:16]}...")
            
            # Check disk cache
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                def read_cache():
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        return data
                
                data = await asyncio.to_thread(read_cache)
                
                if time.time() - data['timestamp'] < self.ttl:
                    logger.info(f"[OK] Cache HIT (disk): {key[:16]}...")
                    
                    # Load into memory cache
                    async with self._lock:
                        self.memory_cache[key] = (data['response'], data['timestamp'])
                    
                    return data['response']
                else:
                    # Expired, delete file
                    cache_file.unlink(missing_ok=True)
                    logger.debug(f"[DEL] Cache expired (disk): {key[:16]}...")
            
            logger.debug(f"[ERROR] Cache MISS: {key[:16]}...")
            return None
        
        except Exception as e:
            logger.warning(f"[WARN] Cache get error: {e}")
            return None
    
    async def set(
        self,
        prompt: str,
        model: str,
        response: str,
        **kwargs
    ):
        """
        Cache response
        
        Args:
            prompt: The prompt text
            model: Model name
            response: AI response to cache
            **kwargs: Additional parameters
        """
        try:
            key = self._generate_key(prompt, model, **kwargs)
            timestamp = time.time()
            
            # Store in memory cache
            async with self._lock:
                # Evict oldest if at capacity
                if len(self.memory_cache) >= self.max_memory_items:
                    oldest_key = min(
                        self.memory_cache.keys(),
                        key=lambda k: self.memory_cache[k][1]
                    )
                    del self.memory_cache[oldest_key]
                    logger.debug(f"[DEL] Evicted oldest cache entry: {oldest_key[:16]}...")
                
                self.memory_cache[key] = (response, timestamp)
            
            # Store in disk cache
            cache_file = self.cache_dir / f"{key}.json"
            
            def write_cache():
                with open(cache_file, 'w') as f:
                    json.dump({
                        'prompt': prompt[:500],  # Store truncated prompt for debugging
                        'model': model,
                        'response': response,
                        'timestamp': timestamp,
                        'kwargs': kwargs
                    }, f)
            
            await asyncio.to_thread(write_cache)
            
            logger.debug(f"[FLOPPY] Cached response: {key[:16]}...")
        
        except Exception as e:
            logger.warning(f"[WARN] Cache set error: {e}")
    
    async def clear(self):
        """Clear all caches"""
        try:
            async with self._lock:
                self.memory_cache.clear()
            
            # Clear disk cache
            def clear_disk():
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
            
            await asyncio.to_thread(clear_disk)
            
            logger.info("[DEL] Cache cleared")
        
        except Exception as e:
            logger.warning(f"[WARN] Cache clear error: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            memory_size = len(self.memory_cache)
            
            def count_disk():
                return len(list(self.cache_dir.glob("*.json")))
            
            disk_size = await asyncio.to_thread(count_disk)
            
            return {
                'memory_items': memory_size,
                'disk_items': disk_size,
                'ttl': self.ttl,
                'max_memory_items': self.max_memory_items,
                'cache_dir': str(self.cache_dir)
            }
        
        except Exception as e:
            logger.warning(f"[WARN] Cache stats error: {e}")
            return {}


# Global cache instance
_global_cache: Optional[AIResponseCache] = None


def get_cache() -> AIResponseCache:
    """Get or create global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = AIResponseCache(
            ttl=3600,  # 1 hour
            max_memory_items=1000
        )
    return _global_cache


async def cached_ai_call(
    ai_function,
    prompt: str,
    model: str,
    use_cache: bool = True,
    **kwargs
) -> str:
    """
    Wrapper for AI calls with automatic caching
    
    Args:
        ai_function: Async function that makes AI call
        prompt: The prompt text
        model: Model name
        use_cache: Whether to use cache
        **kwargs: Additional parameters
        
    Returns:
        AI response (from cache or fresh call)
    """
    if not use_cache:
        return await ai_function(prompt, **kwargs)
    
    cache = get_cache()
    
    # Try to get from cache
    cached_response = await cache.get(prompt, model, **kwargs)
    if cached_response is not None:
        return cached_response
    
    # Make fresh call
    response = await ai_function(prompt, **kwargs)
    
    # Cache the response
    await cache.set(prompt, model, response, **kwargs)
    
    return response

