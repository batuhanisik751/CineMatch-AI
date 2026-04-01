"""Tests for global platform stats endpoint."""

from __future__ import annotations


async def test_global_stats_200(client):
    resp = await client.get("/api/v1/stats/global")

    assert resp.status_code == 200
    data = resp.json()

    assert data["total_movies"] == 29000
    assert data["total_users"] == 162000
    assert data["total_ratings"] == 24700000
    assert data["avg_rating"] == 6.8
    assert data["ratings_this_week"] == 120

    assert data["most_rated_movie"]["title"] == "The Shawshank Redemption"
    assert data["most_rated_movie"]["rating_count"] == 5000

    assert data["highest_rated_movie"]["title"] == "The Godfather"
    assert data["highest_rated_movie"]["avg_user_rating"] == 9.1

    assert data["most_active_user"]["id"] == 42
    assert data["most_active_user"]["rating_count"] == 3000


async def test_global_stats_caches_result(client, mock_cache_service):
    resp = await client.get("/api/v1/stats/global")
    assert resp.status_code == 200

    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "global_stats"
    assert call_args[1]["ttl"] == 3600


async def test_global_stats_returns_cached(client, mock_cache_service, mock_global_stats_service):
    """When cache has data, service should not be called."""
    import json

    cached_data = {
        "total_movies": 100,
        "total_users": 50,
        "total_ratings": 1000,
        "avg_rating": 7.0,
        "most_rated_movie": None,
        "highest_rated_movie": None,
        "most_active_user": None,
        "ratings_this_week": 10,
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)

    resp = await client.get("/api/v1/stats/global")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total_movies"] == 100
    assert data["total_ratings"] == 1000

    mock_global_stats_service.get_global_stats.assert_not_called()
