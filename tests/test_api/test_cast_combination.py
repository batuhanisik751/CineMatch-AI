"""Tests for cast combination endpoint."""

from __future__ import annotations

import json


async def test_by_cast_two_actors(client, sample_movie):
    resp = await client.get(
        "/api/v1/movies/by-cast", params={"actors": "Keanu Reeves,Laurence Fishburne"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["title"] == sample_movie.title
    assert data["actors"] == ["Keanu Reeves", "Laurence Fishburne"]
    assert data["offset"] == 0
    assert data["limit"] == 20


async def test_by_cast_calls_service(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/by-cast", params={"actors": "Actor A,Actor B"})
    assert resp.status_code == 200
    mock_movie_service.movies_by_cast_combination.assert_called_once()
    call_kwargs = mock_movie_service.movies_by_cast_combination.call_args.kwargs
    assert call_kwargs["actors"] == ["Actor A", "Actor B"]
    assert call_kwargs["sort_by"] == "popularity"
    assert call_kwargs["sort_order"] == "desc"
    assert call_kwargs["offset"] == 0
    assert call_kwargs["limit"] == 20


async def test_by_cast_single_actor_returns_400(client):
    resp = await client.get("/api/v1/movies/by-cast", params={"actors": "Keanu Reeves"})
    assert resp.status_code == 400
    assert "At least 2" in resp.json()["detail"]


async def test_by_cast_too_many_actors_returns_400(client):
    actors = ",".join(f"Actor {i}" for i in range(6))
    resp = await client.get("/api/v1/movies/by-cast", params={"actors": actors})
    assert resp.status_code == 400
    assert "At most 5" in resp.json()["detail"]


async def test_by_cast_empty_actors_returns_422(client):
    resp = await client.get("/api/v1/movies/by-cast", params={"actors": ""})
    assert resp.status_code == 422


async def test_by_cast_sort_params(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/by-cast",
        params={"actors": "A,B", "sort_by": "vote_average", "sort_order": "asc"},
    )
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.movies_by_cast_combination.call_args.kwargs
    assert call_kwargs["sort_by"] == "vote_average"
    assert call_kwargs["sort_order"] == "asc"


async def test_by_cast_pagination(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/by-cast",
        params={"actors": "A,B", "offset": 20, "limit": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["offset"] == 20
    assert data["limit"] == 10
    call_kwargs = mock_movie_service.movies_by_cast_combination.call_args.kwargs
    assert call_kwargs["offset"] == 20
    assert call_kwargs["limit"] == 10


async def test_by_cast_empty_results(client, mock_movie_service):
    mock_movie_service.movies_by_cast_combination.return_value = ([], 0)
    resp = await client.get("/api/v1/movies/by-cast", params={"actors": "Unknown A,Unknown B"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["results"] == []


async def test_by_cast_cached(client, mock_movie_service, mock_cache_service):
    cached_data = {
        "actors": ["A", "B"],
        "results": [],
        "total": 0,
        "offset": 0,
        "limit": 20,
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)
    resp = await client.get("/api/v1/movies/by-cast", params={"actors": "A,B"})
    assert resp.status_code == 200
    mock_movie_service.movies_by_cast_combination.assert_not_called()


async def test_by_cast_deduplicates_actors(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/by-cast", params={"actors": "Actor A,Actor A,Actor B"})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.movies_by_cast_combination.call_args.kwargs
    assert call_kwargs["actors"] == ["Actor A", "Actor B"]
