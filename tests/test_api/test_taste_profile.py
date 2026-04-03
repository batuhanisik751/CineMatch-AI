"""Tests for the taste-profile API endpoint."""

from __future__ import annotations

import pytest

from cinematch.schemas.taste_profile import TasteProfileResponse


@pytest.mark.asyncio
async def test_taste_profile_returns_insights(client, mock_taste_profile_service):
    """GET /api/v1/users/{id}/taste-profile returns structured insights."""
    resp = await client.get("/api/v1/users/1/taste-profile")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total_ratings"] == 20
    assert len(data["insights"]) == 4
    assert data["insights"][0]["key"] == "top_genre"
    assert data["llm_summary"] is None


@pytest.mark.asyncio
async def test_taste_profile_cache_hit(client, mock_cache_service, mock_taste_profile_service):
    """Cached response is returned without calling the service."""
    cached_json = TasteProfileResponse(
        user_id=1,
        total_ratings=10,
        insights=[{"key": "top_genre", "icon": "movie_filter", "text": "cached"}],
        llm_summary=None,
    ).model_dump_json()
    mock_cache_service.get.return_value = cached_json

    resp = await client.get("/api/v1/users/1/taste-profile")

    assert resp.status_code == 200
    data = resp.json()
    assert data["insights"][0]["text"] == "cached"
    mock_taste_profile_service.get_taste_profile.assert_not_called()


@pytest.mark.asyncio
async def test_taste_profile_empty_for_new_user(client, mock_taste_profile_service):
    """User with no ratings gets empty insights list."""
    mock_taste_profile_service.get_taste_profile.return_value = {
        "user_id": 1,
        "total_ratings": 0,
        "insights": [],
        "llm_summary": None,
    }

    resp = await client.get("/api/v1/users/1/taste-profile")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_ratings"] == 0
    assert data["insights"] == []
