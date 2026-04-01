"""Tests for GET /api/v1/movies/{movie_id}/rating-stats endpoint."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_rating_stats_success(client):
    resp = await client.get("/api/v1/movies/1/rating-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["movie_id"] == 1
    assert data["avg_rating"] == 7.5
    assert data["median_rating"] == 8.0
    assert data["total_ratings"] == 100
    assert data["stddev"] == 1.58
    assert data["polarization_score"] == 0.35
    assert len(data["distribution"]) == 10
    assert data["user_rating"] is None


@pytest.mark.asyncio
async def test_rating_stats_with_user_id(client, mock_rating_service):
    mock_rating_service.bulk_check.return_value = {1: 8}
    resp = await client.get("/api/v1/movies/1/rating-stats?user_id=42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_rating"] == 8


@pytest.mark.asyncio
async def test_rating_stats_user_not_rated(client, mock_rating_service):
    mock_rating_service.bulk_check.return_value = {}
    resp = await client.get("/api/v1/movies/1/rating-stats?user_id=99")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_rating"] is None


@pytest.mark.asyncio
async def test_rating_stats_invalid_user_id(client):
    resp = await client.get("/api/v1/movies/1/rating-stats?user_id=0")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rating_stats_distribution_structure(client):
    resp = await client.get("/api/v1/movies/1/rating-stats")
    assert resp.status_code == 200
    data = resp.json()
    for bucket in data["distribution"]:
        assert "rating" in bucket
        assert "count" in bucket
        assert isinstance(bucket["rating"], int)
        assert isinstance(bucket["count"], int)


@pytest.mark.asyncio
async def test_rating_stats_cache_hit(client, mock_rating_service, mock_cache_service):
    import json

    cached = json.dumps(
        {
            "movie_id": 1,
            "avg_rating": 6.0,
            "median_rating": 6.0,
            "total_ratings": 50,
            "stddev": 2.0,
            "polarization_score": 0.44,
            "distribution": [{"rating": i, "count": 5} for i in range(1, 11)],
            "user_rating": None,
        }
    )
    mock_cache_service.get.return_value = cached

    resp = await client.get("/api/v1/movies/1/rating-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["avg_rating"] == 6.0
    assert data["total_ratings"] == 50
    mock_rating_service.get_movie_rating_stats.assert_not_called()


@pytest.mark.asyncio
async def test_rating_stats_cache_miss_stores(client, mock_cache_service):
    mock_cache_service.get.return_value = None
    resp = await client.get("/api/v1/movies/1/rating-stats")
    assert resp.status_code == 200
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "movie_rating_stats:1"
    assert call_args[1]["ttl"] == 3600
