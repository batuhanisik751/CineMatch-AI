"""Redis cache service."""

from __future__ import annotations

import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class CacheService:
    """Async Redis wrapper with key-pattern invalidation."""

    def __init__(self, redis_url: str, default_ttl: int = 3600) -> None:
        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._default_ttl = default_ttl

    async def get(self, key: str) -> str | None:
        """Get a cached value."""
        try:
            return await self._redis.get(key)
        except Exception:
            logger.debug("Redis unavailable for GET %s", key)
            return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set a cached value with optional TTL override."""
        try:
            await self._redis.set(key, value, ex=ttl or self._default_ttl)
        except Exception:
            logger.debug("Redis unavailable for SET %s", key)

    async def delete(self, key: str) -> None:
        """Delete a single key."""
        try:
            await self._redis.delete(key)
        except Exception:
            logger.debug("Redis unavailable for DELETE %s", key)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching a glob pattern (e.g. 'recs:42:*')."""
        try:
            cursor = "0"
            while cursor != 0:
                cursor, keys = await self._redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
        except Exception:
            logger.debug("Redis unavailable for DELETE_PATTERN %s", pattern)

    async def invalidate_user_recs(self, user_id: int) -> None:
        """Invalidate all cached recommendations for a user."""
        await self.delete_pattern(f"recs:{user_id}:*")
        await self.delete_pattern(f"mood_rec:{user_id}:*")
        await self.delete_pattern(f"feed:{user_id}:*")
        await self.delete_pattern(f"taste_profile:{user_id}")
        await self.delete_pattern(f"watchlist_recs:{user_id}:*")
        await self.delete_pattern(f"match:{user_id}:*")
        await self.delete(f"achievements:{user_id}")
        logger.debug("Invalidated recommendation cache for user %s", user_id)

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._redis.aclose()
