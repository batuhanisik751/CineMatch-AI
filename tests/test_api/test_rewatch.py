"""API tests for the rewatch endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


@pytest.fixture()
def rewatch_data(sample_movie):
    return {
        "user_id": 1,
        "suggestions": [
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
                "user_rating": 9,
                "rated_at": datetime(2021, 6, 15, tzinfo=UTC).isoformat(),
                "days_since_rated": 1200,
                "is_classic": True,
            }
        ],
        "total": 1,
    }


async def test_rewatch_endpoint_returns_200(client, mock_rewatch_service, rewatch_data):
    mock_rewatch_service.get_rewatch_suggestions.return_value = rewatch_data

    resp = await client.get("/api/v1/users/1/rewatch")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total"] == 1
    assert len(data["suggestions"]) == 1
    assert data["suggestions"][0]["user_rating"] == 9
    assert data["suggestions"][0]["is_classic"] is True
    assert data["suggestions"][0]["movie"]["title"] == "The Matrix"


async def test_rewatch_query_params(client, mock_rewatch_service, rewatch_data):
    mock_rewatch_service.get_rewatch_suggestions.return_value = rewatch_data

    resp = await client.get("/api/v1/users/1/rewatch?limit=5&min_rating=9")

    assert resp.status_code == 200
    call_kwargs = mock_rewatch_service.get_rewatch_suggestions.call_args
    assert call_kwargs.kwargs["limit"] == 5
    assert call_kwargs.kwargs["min_rating"] == 9


async def test_rewatch_empty_result(client, mock_rewatch_service):
    mock_rewatch_service.get_rewatch_suggestions.return_value = {
        "user_id": 1,
        "suggestions": [],
        "total": 0,
    }

    resp = await client.get("/api/v1/users/1/rewatch")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["suggestions"] == []


async def test_rewatch_cache_hit(client, mock_rewatch_service, mock_cache_service, rewatch_data):
    from cinematch.schemas.rewatch import RewatchResponse

    response = RewatchResponse(**rewatch_data)
    mock_cache_service.get.return_value = response.model_dump_json()

    resp = await client.get("/api/v1/users/1/rewatch")

    assert resp.status_code == 200
    # Service should NOT be called when cache hits
    mock_rewatch_service.get_rewatch_suggestions.assert_not_called()
