"""Tests for the blind spots API endpoint."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_blind_spots_returns_200(client, mock_blind_spot_service, sample_movie):
    mock_blind_spot_service.get_blind_spots.return_value = {
        "user_id": 1,
        "genre": None,
        "movies": [
            {
                "movie": {
                    "id": sample_movie.id,
                    "title": sample_movie.title,
                    "genres": sample_movie.genres,
                    "vote_average": sample_movie.vote_average,
                    "release_date": str(sample_movie.release_date),
                    "poster_path": sample_movie.poster_path,
                    "original_language": sample_movie.original_language,
                    "runtime": sample_movie.runtime,
                },
                "vote_count": 20000,
                "popularity_score": 164000.0,
            }
        ],
        "total": 1,
    }

    resp = await client.get("/api/v1/users/1/blind-spots")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total"] == 1
    assert len(data["movies"]) == 1
    assert data["movies"][0]["movie"]["title"] == "The Matrix"
    assert data["movies"][0]["vote_count"] == 20000
    assert data["genre"] is None


@pytest.mark.asyncio
async def test_blind_spots_with_genre_filter(client, mock_blind_spot_service):
    mock_blind_spot_service.get_blind_spots.return_value = {
        "user_id": 1,
        "genre": "Horror",
        "movies": [],
        "total": 0,
    }

    resp = await client.get("/api/v1/users/1/blind-spots?genre=Horror")

    assert resp.status_code == 200
    data = resp.json()
    assert data["genre"] == "Horror"
    mock_blind_spot_service.get_blind_spots.assert_called_once()
    call_kwargs = mock_blind_spot_service.get_blind_spots.call_args
    assert call_kwargs.kwargs["genre"] == "Horror"


@pytest.mark.asyncio
async def test_blind_spots_with_limit(client, mock_blind_spot_service):
    mock_blind_spot_service.get_blind_spots.return_value = {
        "user_id": 1,
        "genre": None,
        "movies": [],
        "total": 0,
    }

    resp = await client.get("/api/v1/users/1/blind-spots?limit=5")

    assert resp.status_code == 200
    call_kwargs = mock_blind_spot_service.get_blind_spots.call_args
    assert call_kwargs.kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_blind_spots_empty_result(client, mock_blind_spot_service):
    resp = await client.get("/api/v1/users/1/blind-spots")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["movies"] == []
