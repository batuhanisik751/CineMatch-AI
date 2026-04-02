"""Tests for predicted match percentage API endpoints."""

from __future__ import annotations

import pytest

from cinematch.services.hybrid_recommender import PredictedMatchResult


@pytest.mark.asyncio
async def test_single_prediction_returns_200(client, mock_hybrid_recommender):
    """GET /api/v1/users/{id}/predicted-rating/{movie_id} returns valid response."""
    mock_hybrid_recommender.predict_match.return_value = [
        PredictedMatchResult(
            movie_id=1, match_percent=87,
            content_score=0.8, collab_score=0.6, alpha=0.5,
        ),
    ]

    resp = await client.get("/api/v1/users/1/predicted-rating/1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert len(data["predictions"]) == 1
    assert data["predictions"][0]["movie_id"] == 1
    assert data["predictions"][0]["match_percent"] == 87
    assert 0 <= data["predictions"][0]["match_percent"] <= 100


@pytest.mark.asyncio
async def test_batch_prediction_returns_200(client, mock_hybrid_recommender):
    """POST /api/v1/users/{id}/predicted-ratings returns correct number of items."""
    mock_hybrid_recommender.predict_match.return_value = [
        PredictedMatchResult(
            movie_id=1, match_percent=87,
            content_score=0.8, collab_score=0.6, alpha=0.5,
        ),
        PredictedMatchResult(
            movie_id=2, match_percent=72,
            content_score=0.6, collab_score=0.5, alpha=0.5,
        ),
        PredictedMatchResult(
            movie_id=3, match_percent=55,
            content_score=0.4, collab_score=0.3, alpha=0.5,
        ),
    ]

    resp = await client.post(
        "/api/v1/users/1/predicted-ratings",
        json={"movie_ids": [1, 2, 3]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert len(data["predictions"]) == 3


@pytest.mark.asyncio
async def test_batch_empty_movie_ids_returns_422(client):
    """POST with empty movie_ids returns validation error."""
    resp = await client.post(
        "/api/v1/users/1/predicted-ratings",
        json={"movie_ids": []},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_too_many_movie_ids_returns_422(client):
    """POST with >100 movie_ids returns validation error."""
    resp = await client.post(
        "/api/v1/users/1/predicted-ratings",
        json={"movie_ids": list(range(1, 102))},  # 101 items
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_single_prediction_no_recommender_returns_503(client, app):
    """GET without recommender returns 503."""
    from cinematch.api.deps import get_hybrid_recommender

    app.dependency_overrides[get_hybrid_recommender] = lambda: None

    resp = await client.get("/api/v1/users/1/predicted-rating/1")

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_batch_no_user_ratings_returns_empty(client, mock_hybrid_recommender):
    """POST for user with no ratings returns empty predictions."""
    mock_hybrid_recommender.predict_match.return_value = []

    resp = await client.post(
        "/api/v1/users/1/predicted-ratings",
        json={"movie_ids": [1, 2]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["predictions"] == []
