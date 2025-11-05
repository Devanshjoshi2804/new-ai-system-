"""
Redis-based caching for OCR results
Improves performance by caching processed documents
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("redis not available - caching will be disabled")

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class OCRCache:
    """
    Redis-based cache for OCR results
    
    Features:
    - File hash-based keys for deduplication
    - Configurable TTL (default 1 hour)
    - Automatic serialization/deserialization
    - Cache hit/miss metrics
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ):
        """
        Initialize OCR cache
        
        Args:
            redis_url: Redis connection URL (defaults to settings.redis_url)
            ttl_seconds: Cache TTL in seconds (defaults to settings.ocr_cache_ttl or 3600)
        """
        self.redis_url = redis_url or getattr(settings, 'redis_url', 'redis://localhost:6379')
        self.ttl_seconds = ttl_seconds or getattr(settings, 'ocr_cache_ttl', 3600)
        self.redis_client: Optional[aioredis.Redis] = None
        self.cache_enabled = REDIS_AVAILABLE
        
        # Metrics
        self.hits = 0
        self.misses = 0
    
    async def connect(self):
        """Connect to Redis"""
        if not self.cache_enabled:
            logger.warning("Redis not available - caching disabled")
            return
        
        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("[OK] Connected to Redis for OCR caching")
        except Exception as e:
            logger.warning(f"[WARN] Failed to connect to Redis: {e}. Caching disabled.")
            self.cache_enabled = False
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    def _make_cache_key(self, file_hash: str, extract_mode: str) -> str:
        """
        Generate cache key
        
        Args:
            file_hash: MD5 hash of file content
            extract_mode: Extraction mode (full, structured, tables)
        
        Returns:
            Cache key string
        """
        return f"ocr:{file_hash}:{extract_mode}"
    
    async def get(
        self,
        file_hash: str,
        extract_mode: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get OCR result from cache
        
        Args:
            file_hash: MD5 hash of file content
            extract_mode: Extraction mode used
        
        Returns:
            Cached result dict or None if not found
        """
        if not self.cache_enabled or not self.redis_client:
            return None
        
        try:
            key = self._make_cache_key(file_hash, extract_mode)
            cached_data = await self.redis_client.get(key)
            
            if cached_data:
                self.hits += 1
                logger.info(f"[OK] Cache HIT for {key}")
                return json.loads(cached_data)
            else:
                self.misses += 1
                logger.debug(f"[ERROR] Cache MISS for {key}")
                return None
        
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None
    
    async def set(
        self,
        file_hash: str,
        extract_mode: str,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store OCR result in cache
        
        Args:
            file_hash: MD5 hash of file content
            extract_mode: Extraction mode used
            result: OCR result to cache
            ttl: Time-to-live in seconds (defaults to self.ttl_seconds)
        
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.cache_enabled or not self.redis_client:
            return False
        
        try:
            key = self._make_cache_key(file_hash, extract_mode)
            ttl = ttl or self.ttl_seconds
            
            # Serialize result
            serialized = json.dumps(result)
            
            # Store in Redis with TTL
            await self.redis_client.setex(
                key,
                timedelta(seconds=ttl),
                serialized
            )
            
            logger.info(f"[FLOPPY] Cached result for {key} (TTL: {ttl}s)")
            return True
        
        except Exception as e:
            logger.error(f"Error writing to cache: {e}")
            return False
    
    async def delete(self, file_hash: str, extract_mode: str) -> bool:
        """
        Delete cached result
        
        Args:
            file_hash: MD5 hash of file content
            extract_mode: Extraction mode
        
        Returns:
            True if deleted, False otherwise
        """
        if not self.cache_enabled or not self.redis_client:
            return False
        
        try:
            key = self._make_cache_key(file_hash, extract_mode)
            deleted = await self.redis_client.delete(key)
            
            if deleted:
                logger.info(f"[DEL] Deleted cache for {key}")
            
            return bool(deleted)
        
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False
    
    async def clear_all(self) -> int:
        """
        Clear all OCR cache entries
        
        Returns:
            Number of keys deleted
        """
        if not self.cache_enabled or not self.redis_client:
            return 0
        
        try:
            # Find all OCR cache keys
            keys = []
            async for key in self.redis_client.scan_iter(match="ocr:*"):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"[DEL] Cleared {deleted} OCR cache entries")
                return deleted
            
            return 0
        
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict with hits, misses, and hit rate
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_enabled": self.cache_enabled
        }
    
    def reset_stats(self):
        """Reset cache statistics"""
        self.hits = 0
        self.misses = 0
        logger.info("Reset cache statistics")


# Singleton instance
_cache: Optional[OCRCache] = None


async def get_ocr_cache() -> OCRCache:
    """
    Get or create singleton OCR cache instance
    
    Returns:
        OCRCache instance
    """
    global _cache
    if _cache is None:
        _cache = OCRCache()
        await _cache.connect()
    return _cache


async def cached_ocr_extract(
    file_content: bytes,
    extract_mode: str,
    ocr_function,
    *args,
    **kwargs
) -> Dict[str, Any]:
    """
    Helper function to extract with caching
    
    Args:
        file_content: File content as bytes
        extract_mode: Extraction mode
        ocr_function: Function to call if cache miss
        *args, **kwargs: Arguments to pass to ocr_function
    
    Returns:
        OCR result (from cache or fresh)
    """
    from src.infrastructure.ai.ocr_service import PixtralOCRService
    
    # Calculate file hash
    file_hash = PixtralOCRService.calculate_file_hash(file_content)
    
    # Try cache first
    cache = await get_ocr_cache()
    cached_result = await cache.get(file_hash, extract_mode)
    
    if cached_result:
        logger.info("[OK] Returning cached OCR result")
        cached_result["from_cache"] = True
        return cached_result
    
    # Cache miss - call OCR function
    logger.info("[INFO] Cache miss - performing OCR")
    result = await ocr_function(*args, **kwargs)
    
    # Cache the result
    await cache.set(file_hash, extract_mode, result)
    result["from_cache"] = False
    
    return result


