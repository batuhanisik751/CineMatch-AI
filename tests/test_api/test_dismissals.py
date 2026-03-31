"""Tests for dismissal API endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_dismiss_movie_success(client, sample_dismissal, sample_movie):
    resp = await client.post(
        "/api/v1/users/1/dismissals",
        json={"movie_id": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == 1
    assert data["movie_id"] == 1
    assert data["movie_title"] == sample_movie.title
    assert "dismissed_at" in data


@pytest.mark.asyncio
async def test_dismiss_movie_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.post(
        "/api/v1/users/1/dismissals",
        json={"movie_id": 999},
    )
    assert resp.status_code == 404
    assert "Movie not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_undismiss_movie_success(client):
    resp = await client.delete("/api/v1/users/1/dismissals/1")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_undismiss_movie_not_found(client, mock_dismissal_service):
    mock_dismissal_service.undismiss_movie.return_value = False
    resp = await client.delete("/api/v1/users/1/dismissals/999")
    assert resp.status_code == 404
    assert "not dismissed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_dismissals_success(client):
    resp = await client.get("/api/v1/users/1/dismissals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["movie_title"] == "The Matrix"


@pytest.mark.asyncio
async def test_get_dismissals_empty(client, mock_dismissal_service):
    mock_dismissal_service.get_dismissals.return_value = ([], 0)
    resp = await client.get("/api/v1/users/1/dismissals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_bulk_check_dismissals(client):
    resp = await client.get("/api/v1/users/1/dismissals/check?movie_ids=1,2,3")
    assert resp.status_code == 200
    data = resp.json()
    assert "movie_ids" in data
    assert isinstance(data["movie_ids"], list)


@pytest.mark.asyncio
async def test_bulk_check_invalid_ids(client):
    resp = await client.get("/api/v1/users/1/dismissals/check?movie_ids=abc,def")
    assert resp.status_code == 422
