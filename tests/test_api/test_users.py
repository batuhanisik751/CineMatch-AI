"""Tests for user API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


async def test_get_user_success(client, mock_db, sample_user):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(return_value=result_mock)

    resp = await client.get(f"/api/v1/users/{sample_user.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sample_user.id
    assert data["movielens_id"] == sample_user.movielens_id


async def test_get_user_not_found(client, mock_db):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    resp = await client.get("/api/v1/users/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


async def test_get_user_stats_success(client, mock_user_stats_service):
    resp = await client.get("/api/v1/users/1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total_ratings"] == 5
    assert data["average_rating"] == 3.8
    assert len(data["genre_distribution"]) == 2
    assert len(data["rating_distribution"]) == 10
    assert len(data["top_directors"]) == 1
    assert len(data["top_actors"]) == 1
    assert len(data["rating_timeline"]) == 1
    mock_user_stats_service.get_user_stats.assert_called_once()


async def test_get_user_stats_empty(client, mock_user_stats_service):
    mock_user_stats_service.get_user_stats.return_value = {
        "user_id": 999,
        "total_ratings": 0,
        "average_rating": 0.0,
        "genre_distribution": [],
        "rating_distribution": [{"rating": str(v), "count": 0} for v in range(1, 11)],
        "top_directors": [],
        "top_actors": [],
        "rating_timeline": [],
    }
    resp = await client.get("/api/v1/users/999/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_ratings"] == 0
    assert data["average_rating"] == 0.0
    assert data["genre_distribution"] == []


async def test_surprise_me_success(client, mock_user_stats_service, mock_movie_service, mock_db):
    """Surprise endpoint returns movies outside user's top genres."""
    rated_result_mock = MagicMock()
    rated_result_mock.all.return_value = [(10,), (20,)]
    mock_db.execute = AsyncMock(return_value=rated_result_mock)

    resp = await client.get("/api/v1/users/1/surprise?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["excluded_genres"] == ["Action", "Comedy"]
    assert data["limit"] == 5
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "The Matrix"
    mock_movie_service.surprise_movies.assert_called_once()


async def test_surprise_me_no_ratings(client, mock_user_stats_service, mock_movie_service, mock_db):
    """User with no ratings gets surprise movies with no genre exclusions."""
    mock_user_stats_service.get_user_stats.return_value = {
        "user_id": 999,
        "total_ratings": 0,
        "average_rating": 0.0,
        "genre_distribution": [],
        "rating_distribution": [],
        "top_directors": [],
        "top_actors": [],
        "rating_timeline": [],
    }
    rated_result_mock = MagicMock()
    rated_result_mock.all.return_value = []
    mock_db.execute = AsyncMock(return_value=rated_result_mock)

    resp = await client.get("/api/v1/users/999/surprise?limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["excluded_genres"] == []
    assert data["limit"] == 3


async def test_surprise_me_default_limit(
    client, mock_user_stats_service, mock_movie_service, mock_db
):
    """Default limit is 5 when not specified."""
    rated_result_mock = MagicMock()
    rated_result_mock.all.return_value = []
    mock_db.execute = AsyncMock(return_value=rated_result_mock)

    resp = await client.get("/api/v1/users/1/surprise")
    assert resp.status_code == 200
    assert resp.json()["limit"] == 5


async def test_completions_success(client, mock_movie_service):
    """Completions endpoint returns collection groups."""
    resp = await client.get("/api/v1/users/1/completions?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert len(data["groups"]) == 1
    group = data["groups"][0]
    assert group["creator_type"] == "director"
    assert group["creator_name"] == "Lana Wachowski"
    assert group["rated_count"] == 3
    assert group["avg_rating"] == 8.0
    assert group["total_by_creator"] == 5
    assert len(group["missing"]) == 1
    assert group["missing"][0]["title"] == "The Matrix"
    assert data["total_missing"] == 1
    mock_movie_service.collection_completions.assert_called_once()


async def test_completions_empty(client, mock_movie_service):
    """User with no qualifying creators gets empty groups."""
    mock_movie_service.collection_completions.return_value = []
    resp = await client.get("/api/v1/users/999/completions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["groups"] == []
    assert data["total_missing"] == 0


async def test_completions_custom_limit(client, mock_movie_service):
    """Limit parameter is passed through to service."""
    resp = await client.get("/api/v1/users/1/completions?limit=25")
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.collection_completions.call_args
    assert call_kwargs.kwargs["limit"] == 25
