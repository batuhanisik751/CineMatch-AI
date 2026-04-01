"""Tests for the achievements API endpoint."""

from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_get_achievements_success(client, mock_achievement_service):
    resp = await client.get("/api/v1/users/1/achievements")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total_count"] == 12
    assert len(data["badges"]) == 12
    assert data["unlocked_count"] == 5
    mock_achievement_service.get_achievements.assert_called_once()


@pytest.mark.asyncio
async def test_get_achievements_cached(client, mock_achievement_service, mock_cache_service):
    cached_data = {
        "user_id": 1,
        "badges": [
            {
                "id": "first_rating",
                "name": "First Rating",
                "description": "Rate your first movie",
                "icon": "star",
                "unlocked": True,
                "progress": 1,
                "target": 1,
                "unlocked_detail": None,
            }
        ],
        "unlocked_count": 1,
        "total_count": 12,
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)

    resp = await client.get("/api/v1/users/1/achievements")
    assert resp.status_code == 200
    data = resp.json()
    assert data["unlocked_count"] == 1
    mock_achievement_service.get_achievements.assert_not_called()


@pytest.mark.asyncio
async def test_get_achievements_no_ratings(client, mock_achievement_service):
    mock_achievement_service.get_achievements.return_value = {
        "user_id": 1,
        "badges": [
            {
                "id": "first_rating",
                "name": "First Rating",
                "description": "Rate your first movie",
                "icon": "star",
                "unlocked": False,
                "progress": 0,
                "target": 1,
                "unlocked_detail": None,
            }
        ],
        "unlocked_count": 0,
        "total_count": 12,
    }

    resp = await client.get("/api/v1/users/1/achievements")
    assert resp.status_code == 200
    data = resp.json()
    assert data["unlocked_count"] == 0
    assert data["badges"][0]["unlocked"] is False
