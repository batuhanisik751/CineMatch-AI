"""Tests for onboarding API endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_get_onboarding_movies_success(client, mock_onboarding_service):
    """GET /onboarding/movies returns genre-diverse movies."""
    resp = await client.get("/api/v1/onboarding/movies", params={"user_id": 1})

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total"] == 1
    assert len(data["movies"]) == 1
    assert data["movies"][0]["title"] == "The Matrix"
    mock_onboarding_service.get_onboarding_movies.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_onboarding_movies_custom_count(client, mock_onboarding_service):
    """GET /onboarding/movies respects count parameter."""
    resp = await client.get("/api/v1/onboarding/movies", params={"user_id": 1, "count": 15})

    assert resp.status_code == 200
    # Verify the service was called with count=15
    call_args = mock_onboarding_service.get_onboarding_movies.call_args
    assert call_args[0][1] == 15  # second positional arg is count


@pytest.mark.asyncio
async def test_get_onboarding_movies_invalid_count(client):
    """GET /onboarding/movies rejects count outside 10-30 range."""
    resp = await client.get("/api/v1/onboarding/movies", params={"user_id": 1, "count": 5})
    assert resp.status_code == 422

    resp = await client.get("/api/v1/onboarding/movies", params={"user_id": 1, "count": 50})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_onboarding_movies_missing_user_id(client):
    """GET /onboarding/movies requires user_id."""
    resp = await client.get("/api/v1/onboarding/movies")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_onboarding_status_incomplete(client, mock_onboarding_service):
    """GET /onboarding/status returns incomplete status."""
    resp = await client.get("/api/v1/onboarding/status", params={"user_id": 1})

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["completed"] is False
    assert data["rating_count"] == 3
    assert data["threshold"] == 10


@pytest.mark.asyncio
async def test_get_onboarding_status_completed(client, mock_onboarding_service):
    """GET /onboarding/status returns completed status."""
    mock_onboarding_service.get_onboarding_status.return_value = {
        "user_id": 1,
        "completed": True,
        "rating_count": 15,
        "threshold": 10,
    }

    resp = await client.get("/api/v1/onboarding/status", params={"user_id": 1})

    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is True
    assert data["rating_count"] == 15
