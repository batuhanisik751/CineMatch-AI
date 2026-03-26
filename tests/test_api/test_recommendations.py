"""Tests for recommendation API endpoints."""

from __future__ import annotations


async def test_get_recommendations_success(client, sample_movie, mock_movie_service):
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["strategy"] == "hybrid"
    assert len(data["recommendations"]) > 0
    assert "score" in data["recommendations"][0]
    assert "movie" in data["recommendations"][0]


async def test_get_recommendations_content_strategy(client, mock_hybrid_recommender):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"strategy": "content"},
    )
    assert resp.status_code == 200
    mock_hybrid_recommender.recommend.assert_called_once()
    call_kwargs = mock_hybrid_recommender.recommend.call_args
    assert call_kwargs.kwargs.get("strategy") == "content"


async def test_get_recommendations_collab_strategy(client, mock_hybrid_recommender):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"strategy": "collab"},
    )
    assert resp.status_code == 200


async def test_get_recommendations_invalid_strategy(client):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"strategy": "invalid"},
    )
    assert resp.status_code == 422


async def test_get_recommendations_with_top_k(client, mock_hybrid_recommender):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"top_k": 5},
    )
    assert resp.status_code == 200
    mock_hybrid_recommender.recommend.assert_called_once()


async def test_get_recommendations_empty_results(
    client, mock_hybrid_recommender, mock_movie_service
):
    mock_hybrid_recommender.recommend.return_value = []
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendations"] == []
