"""Tests for the streaks API endpoint."""

from __future__ import annotations

import json


async def test_get_streaks_success(client, mock_streak_service):
    resp = await client.get("/api/v1/users/1/streaks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["current_streak"] == 5
    assert data["longest_streak"] == 12
    assert data["total_ratings"] == 87
    assert len(data["milestones"]) == 7
    reached = [m for m in data["milestones"] if m["reached"]]
    assert len(reached) == 3
    mock_streak_service.get_streaks.assert_called_once()


async def test_get_streaks_cached(client, mock_streak_service, mock_cache_service):
    cached_data = {
        "user_id": 1,
        "current_streak": 3,
        "longest_streak": 8,
        "total_ratings": 42,
        "milestones": [
            {"threshold": 10, "reached": True, "label": "10 Ratings"},
            {"threshold": 25, "reached": True, "label": "25 Ratings"},
            {"threshold": 50, "reached": False, "label": "50 Ratings"},
            {"threshold": 100, "reached": False, "label": "100 Ratings"},
            {"threshold": 250, "reached": False, "label": "250 Ratings"},
            {"threshold": 500, "reached": False, "label": "500 Ratings"},
            {"threshold": 1000, "reached": False, "label": "1000 Ratings"},
        ],
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)

    resp = await client.get("/api/v1/users/1/streaks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_streak"] == 3
    assert data["total_ratings"] == 42
    mock_streak_service.get_streaks.assert_not_called()


async def test_get_streaks_no_ratings(client, mock_streak_service):
    mock_streak_service.get_streaks.return_value = {
        "user_id": 1,
        "current_streak": 0,
        "longest_streak": 0,
        "total_ratings": 0,
        "milestones": [
            {"threshold": t, "reached": False, "label": f"{t} Ratings"}
            for t in [10, 25, 50, 100, 250, 500, 1000]
        ],
    }

    resp = await client.get("/api/v1/users/1/streaks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_streak"] == 0
    assert data["longest_streak"] == 0
    assert data["total_ratings"] == 0
    assert all(not m["reached"] for m in data["milestones"])
