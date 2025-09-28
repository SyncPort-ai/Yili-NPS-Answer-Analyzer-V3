"""
Caching layer for NPS V3 API.
Provides in-memory and optional Redis caching for LLM responses and analysis results.
"""

import json
import hashlib
import time
import asyncio
import logging
from typing import Any, Dict, Optional, Callable, TypeVar, Union
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict
import pickle

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

from ..config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheStats:
    """Cache statistics tracker"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.errors = 0
        self.total_size_bytes = 0
        self.start_time = time.time()

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def uptime_seconds(self) -> float:
        """Get cache uptime in seconds"""
        return time.time() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "errors": self.errors,
            "hit_rate": self.hit_rate,
            "total_size_bytes": self.total_size_bytes,
            "uptime_seconds": self.uptime_seconds
        }


class LRUCache:
    """
    Thread-safe LRU cache implementation.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items
            ttl_seconds: Time to live for cache entries
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._lock = asyncio.Lock()
        self.stats = CacheStats()

    def _make_key(self, key: Union[str, Dict, tuple]) -> str:
        """Generate cache key from various input types"""
        if isinstance(key, str):
            return key
        elif isinstance(key, dict):
            # Sort dict for consistent hashing
            sorted_dict = json.dumps(key, sort_keys=True)
            return hashlib.md5(sorted_dict.encode()).hexdigest()
        elif isinstance(key, tuple):
            return hashlib.md5(str(key).encode()).hexdigest()
        else:
            return hashlib.md5(str(key).encode()).hexdigest()

    async def get(self, key: Union[str, Dict, tuple]) -> Optional[Any]:
        """Get item from cache"""
        cache_key = self._make_key(key)

        async with self._lock:
            if cache_key in self._cache:
                # Check TTL
                entry = self._cache[cache_key]
                if time.time() - entry["timestamp"] > self.ttl_seconds:
                    # Expired
                    del self._cache[cache_key]
                    self.stats.evictions += 1
                    self.stats.misses += 1
                    return None

                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                self.stats.hits += 1
                return entry["value"]

            self.stats.misses += 1
            return None

    async def set(
        self,
        key: Union[str, Dict, tuple],
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set item in cache"""
        cache_key = self._make_key(key)
        ttl = ttl or self.ttl_seconds

        async with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size:
                if self._cache:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    self.stats.evictions += 1

            # Add new entry
            self._cache[cache_key] = {
                "value": value,
                "timestamp": time.time(),
                "ttl": ttl
            }

            # Update stats
            try:
                size = len(pickle.dumps(value))
                self.stats.total_size_bytes += size
            except:
                pass

    async def delete(self, key: Union[str, Dict, tuple]) -> bool:
        """Delete item from cache"""
        cache_key = self._make_key(key)

        async with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self.stats.evictions += len(self._cache)

    async def size(self) -> int:
        """Get current cache size"""
        async with self._lock:
            return len(self._cache)


class RedisCache:
    """
    Redis-based distributed cache.
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "nps_v3",
        ttl_seconds: int = 3600
    ):
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all keys
            ttl_seconds: Default TTL for cache entries
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not installed")

        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds
        self._client: Optional[aioredis.Redis] = None
        self.stats = CacheStats()

    async def connect(self) -> None:
        """Connect to Redis"""
        if not self._client:
            self._client = await aioredis.from_url(
                self.redis_url,
                decode_responses=False
            )
            logger.info(f"Connected to Redis at {self.redis_url}")

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._client:
            await self._client.close()
            self._client = None

    def _make_key(self, key: Union[str, Dict, tuple]) -> str:
        """Generate Redis key with prefix"""
        if isinstance(key, str):
            base_key = key
        elif isinstance(key, dict):
            sorted_dict = json.dumps(key, sort_keys=True)
            base_key = hashlib.md5(sorted_dict.encode()).hexdigest()
        else:
            base_key = hashlib.md5(str(key).encode()).hexdigest()

        return f"{self.key_prefix}:{base_key}"

    async def get(self, key: Union[str, Dict, tuple]) -> Optional[Any]:
        """Get item from cache"""
        if not self._client:
            await self.connect()

        redis_key = self._make_key(key)

        try:
            data = await self._client.get(redis_key)

            if data:
                self.stats.hits += 1
                return pickle.loads(data)

            self.stats.misses += 1
            return None

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self.stats.errors += 1
            return None

    async def set(
        self,
        key: Union[str, Dict, tuple],
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set item in cache"""
        if not self._client:
            await self.connect()

        redis_key = self._make_key(key)
        ttl = ttl or self.ttl_seconds

        try:
            data = pickle.dumps(value)
            await self._client.setex(redis_key, ttl, data)

            self.stats.total_size_bytes += len(data)

        except Exception as e:
            logger.error(f"Redis set error: {e}")
            self.stats.errors += 1

    async def delete(self, key: Union[str, Dict, tuple]) -> bool:
        """Delete item from cache"""
        if not self._client:
            await self.connect()

        redis_key = self._make_key(key)

        try:
            result = await self._client.delete(redis_key)
            return result > 0

        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            self.stats.errors += 1
            return False

    async def clear(self, pattern: str = "*") -> None:
        """Clear cache entries matching pattern"""
        if not self._client:
            await self.connect()

        try:
            pattern_key = f"{self.key_prefix}:{pattern}"
            cursor = 0

            while True:
                cursor, keys = await self._client.scan(
                    cursor,
                    match=pattern_key,
                    count=100
                )

                if keys:
                    await self._client.delete(*keys)
                    self.stats.evictions += len(keys)

                if cursor == 0:
                    break

        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            self.stats.errors += 1


class HybridCache:
    """
    Hybrid cache using both in-memory LRU and Redis.
    Provides fast local cache with distributed backup.
    """

    def __init__(
        self,
        lru_size: int = 100,
        ttl_seconds: int = 3600,
        redis_url: Optional[str] = None
    ):
        """
        Initialize hybrid cache.

        Args:
            lru_size: Size of local LRU cache
            ttl_seconds: TTL for cache entries
            redis_url: Optional Redis URL for distributed caching
        """
        self.lru_cache = LRUCache(max_size=lru_size, ttl_seconds=ttl_seconds)
        self.redis_cache: Optional[RedisCache] = None

        if redis_url and REDIS_AVAILABLE:
            self.redis_cache = RedisCache(
                redis_url=redis_url,
                ttl_seconds=ttl_seconds
            )

    async def get(self, key: Union[str, Dict, tuple]) -> Optional[Any]:
        """Get from LRU first, then Redis"""
        # Try LRU cache first
        value = await self.lru_cache.get(key)

        if value is not None:
            return value

        # Try Redis if available
        if self.redis_cache:
            value = await self.redis_cache.get(key)

            if value is not None:
                # Populate LRU cache
                await self.lru_cache.set(key, value)

            return value

        return None

    async def set(
        self,
        key: Union[str, Dict, tuple],
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set in both caches"""
        # Set in LRU
        await self.lru_cache.set(key, value, ttl)

        # Set in Redis if available
        if self.redis_cache:
            await self.redis_cache.set(key, value, ttl)

    async def delete(self, key: Union[str, Dict, tuple]) -> bool:
        """Delete from both caches"""
        lru_result = await self.lru_cache.delete(key)

        redis_result = False
        if self.redis_cache:
            redis_result = await self.redis_cache.delete(key)

        return lru_result or redis_result

    async def clear(self) -> None:
        """Clear both caches"""
        await self.lru_cache.clear()

        if self.redis_cache:
            await self.redis_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics"""
        stats = {
            "lru": self.lru_cache.stats.to_dict()
        }

        if self.redis_cache:
            stats["redis"] = self.redis_cache.stats.to_dict()

        return stats


class CacheManager:
    """
    Main cache manager for NPS V3 API.
    """

    def __init__(self):
        """Initialize cache manager"""
        settings = get_settings()

        # Initialize hybrid cache
        self.cache = HybridCache(
            lru_size=100,
            ttl_seconds=settings.cache_ttl,
            redis_url=settings.redis_url
        )

        # Specialized caches
        self.llm_cache = LRUCache(max_size=500, ttl_seconds=3600)
        self.analysis_cache = LRUCache(max_size=100, ttl_seconds=7200)

    def cache_key_for_llm(
        self,
        prompt: str,
        model: str,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate cache key for LLM requests"""
        return {
            "type": "llm",
            "prompt_hash": hashlib.md5(prompt.encode()).hexdigest(),
            "model": model,
            "temperature": temperature
        }

    def cache_key_for_analysis(
        self,
        workflow_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """Generate cache key for analysis results"""
        return {
            "type": "analysis",
            "workflow_id": workflow_id,
            "agent_id": agent_id
        }

    async def get_llm_response(
        self,
        prompt: str,
        model: str,
        temperature: float
    ) -> Optional[str]:
        """Get cached LLM response"""
        key = self.cache_key_for_llm(prompt, model, temperature)
        return await self.llm_cache.get(key)

    async def set_llm_response(
        self,
        prompt: str,
        model: str,
        temperature: float,
        response: str
    ) -> None:
        """Cache LLM response"""
        key = self.cache_key_for_llm(prompt, model, temperature)
        await self.llm_cache.set(key, response)

    async def get_analysis_result(
        self,
        workflow_id: str,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        key = self.cache_key_for_analysis(workflow_id, agent_id)
        return await self.analysis_cache.get(key)

    async def set_analysis_result(
        self,
        workflow_id: str,
        agent_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Cache analysis result"""
        key = self.cache_key_for_analysis(workflow_id, agent_id)
        await self.analysis_cache.set(key, result)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "main": self.cache.get_stats(),
            "llm": self.llm_cache.stats.to_dict(),
            "analysis": self.analysis_cache.stats.to_dict()
        }


def cached(
    ttl_seconds: int = 3600,
    cache_key_func: Optional[Callable] = None
):
    """
    Decorator for caching async function results.

    Args:
        ttl_seconds: Cache TTL
        cache_key_func: Custom function to generate cache key
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = LRUCache(max_size=100, ttl_seconds=ttl_seconds)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                key = cache_key_func(*args, **kwargs)
            else:
                key = (func.__name__, args, tuple(sorted(kwargs.items())))

            # Try cache
            result = await cache.get(key)

            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result

            # Call function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(key, result)

            return result

        wrapper.cache = cache
        return wrapper

    return decorator


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = CacheManager()

    return _cache_manager