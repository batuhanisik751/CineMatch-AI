"""Tests for CacheService with mocked Redis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.core.cache import CacheService


@pytest.fixture()
def mock_redis():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock()
    r.delete = AsyncMock()
    r.scan = AsyncMock(return_value=(0, []))
    r.aclose = AsyncMock()
    return r


@pytest.fixture()
def cache_service(mock_redis, monkeypatch):
    monkeypatch.setattr(
        "cinematch.core.cache.aioredis",
        MagicMock(from_url=MagicMock(return_value=mock_redis)),
    )
    return CacheService(redis_url="redis://fake:6379/0", default_ttl=60)


@pytest.mark.asyncio
async def test_get_returns_cached_value(cache_service, mock_redis):
    mock_redis.get.return_value = '{"data": "test"}'
    result = await cache_service.get("key1")
    assert result == '{"data": "test"}'
    mock_redis.get.assert_called_once_with("key1")


@pytest.mark.asyncio
async def test_set_stores_value_with_ttl(cache_service, mock_redis):
    await cache_service.set("key1", "value1", ttl=120)
    mock_redis.set.assert_called_once_with("key1", "value1", ex=120)


@pytest.mark.asyncio
async def test_set_uses_default_ttl(cache_service, mock_redis):
    await cache_service.set("key1", "value1")
    mock_redis.set.assert_called_once_with("key1", "value1", ex=60)


@pytest.mark.asyncio
async def test_delete_removes_key(cache_service, mock_redis):
    await cache_service.delete("key1")
    mock_redis.delete.assert_called_once_with("key1")


@pytest.mark.asyncio
async def test_invalidate_user_recs(cache_service, mock_redis):
    # scan is called twice: once for recs:42:* and once for mood_rec:42:*
    mock_redis.scan.side_effect = [
        (0, ["recs:42:hybrid:20", "recs:42:content:10"]),
        (0, ["mood_rec:42:abc:0.3:20"]),
    ]
    await cache_service.invalidate_user_recs(42)
    assert mock_redis.delete.call_count == 2
    mock_redis.delete.assert_any_call("recs:42:hybrid:20", "recs:42:content:10")
    mock_redis.delete.assert_any_call("mood_rec:42:abc:0.3:20")


@pytest.mark.asyncio
async def test_close(cache_service, mock_redis):
    await cache_service.close()
    mock_redis.aclose.assert_called_once()
