"""Tests for the challenges API endpoints."""

from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_get_current_challenges_success(client, mock_challenge_service):
    resp = await client.get("/api/v1/challenges/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["week"] == "2026-W14"
    assert len(data["challenges"]) == 3
    mock_challenge_service.get_current_challenges.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_challenges_cached(client, mock_challenge_service, mock_cache_service):
    cached_data = {
        "week": "2026-W14",
        "challenges": [
            {
                "id": "genre_horror_2026w14",
                "template": "genre",
                "title": "Rate 5 Horror movies",
                "description": "Explore the Horror genre this week",
                "icon": "movie_filter",
                "target": 5,
                "parameter": "Horror",
            }
        ],
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)

    resp = await client.get("/api/v1/challenges/current")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["challenges"]) == 1
    mock_challenge_service.get_current_challenges.assert_not_called()


@pytest.mark.asyncio
async def test_get_challenge_progress_success(client, mock_challenge_service):
    resp = await client.get("/api/v1/users/1/challenges/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["week"] == "2026-W14"
    assert len(data["challenges"]) == 3
    assert data["completed_count"] == 1
    assert data["total_count"] == 3
    mock_challenge_service.get_user_progress.assert_called_once()


@pytest.mark.asyncio
async def test_get_challenge_progress_cached(client, mock_challenge_service, mock_cache_service):
    cached_data = {
        "user_id": 1,
        "week": "2026-W14",
        "challenges": [
            {
                "id": "genre_horror_2026w14",
                "template": "genre",
                "title": "Rate 5 Horror movies",
                "description": "Explore the Horror genre this week",
                "icon": "movie_filter",
                "target": 5,
                "parameter": "Horror",
                "progress": 3,
                "completed": False,
                "qualifying_movie_ids": [1, 2, 3],
            }
        ],
        "completed_count": 0,
        "total_count": 1,
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)

    resp = await client.get("/api/v1/users/1/challenges/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed_count"] == 0
    mock_challenge_service.get_user_progress.assert_not_called()
