"""Tests for watchlist API endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_add_to_watchlist_success(client, sample_watchlist_item, sample_movie):
    resp = await client.post(
        "/api/v1/users/1/watchlist",
        json={"movie_id": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == 1
    assert data["movie_id"] == 1
    assert data["movie_title"] == sample_movie.title
    assert "added_at" in data


@pytest.mark.asyncio
async def test_add_to_watchlist_movie_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.post(
        "/api/v1/users/1/watchlist",
        json={"movie_id": 999},
    )
    assert resp.status_code == 404
    assert "Movie not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_remove_from_watchlist_success(client):
    resp = await client.delete("/api/v1/users/1/watchlist/1")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_remove_from_watchlist_not_found(client, mock_watchlist_service):
    mock_watchlist_service.remove_from_watchlist.return_value = False
    resp = await client.delete("/api/v1/users/1/watchlist/999")
    assert resp.status_code == 404
    assert "not in watchlist" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_watchlist_success(client, sample_watchlist_item, sample_movie):
    resp = await client.get("/api/v1/users/1/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["movie_title"] == "The Matrix"


@pytest.mark.asyncio
async def test_get_watchlist_empty(client, mock_watchlist_service):
    mock_watchlist_service.get_watchlist.return_value = ([], 0)
    resp = await client.get("/api/v1/users/1/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_bulk_check_watchlist(client):
    resp = await client.get("/api/v1/users/1/watchlist/check?movie_ids=1,2,3")
    assert resp.status_code == 200
    data = resp.json()
    assert "movie_ids" in data
    assert isinstance(data["movie_ids"], list)


@pytest.mark.asyncio
async def test_bulk_check_invalid_ids(client):
    resp = await client.get("/api/v1/users/1/watchlist/check?movie_ids=abc,def")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_bulk_check_watchlist_too_many_ids(client):
    ids = ",".join(str(i) for i in range(1, 202))  # 201 IDs
    resp = await client.get(f"/api/v1/users/1/watchlist/check?movie_ids={ids}")
    assert resp.status_code == 400
    assert "Too many IDs" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_watchlist_recommendations_success(client):
    resp = await client.get("/api/v1/users/1/watchlist/recommendations?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["strategy"] == "watchlist"
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["feature_explanations"] == ["Based on your watchlist"]


@pytest.mark.asyncio
async def test_watchlist_recommendations_empty_watchlist(client, mock_watchlist_service):
    mock_watchlist_service.get_watchlist_movie_ids.return_value = []
    resp = await client.get("/api/v1/users/1/watchlist/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "watchlist"
    assert data["recommendations"] == []


@pytest.mark.asyncio
async def test_watchlist_recommendations_service_unavailable(client, app):
    from cinematch.api.deps import get_hybrid_recommender

    app.dependency_overrides[get_hybrid_recommender] = lambda: None
    resp = await client.get("/api/v1/users/1/watchlist/recommendations")
    assert resp.status_code == 503
