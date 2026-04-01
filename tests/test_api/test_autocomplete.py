"""Tests for the autocomplete endpoint."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_autocomplete_returns_suggestions(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/autocomplete", params={"q": "matrix"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "matrix"
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["id"] == 1
    assert result["title"] == "The Matrix"
    assert result["year"] == 1999
    assert result["poster_path"] == "/poster.jpg"
    mock_movie_service.autocomplete.assert_awaited_once()


@pytest.mark.asyncio
async def test_autocomplete_empty_query_returns_422(client):
    resp = await client.get("/api/v1/movies/autocomplete", params={"q": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_autocomplete_limit_respected(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/autocomplete", params={"q": "a", "limit": 3})
    assert resp.status_code == 200
    mock_movie_service.autocomplete.assert_awaited_once()
    call_kwargs = mock_movie_service.autocomplete.call_args
    assert call_kwargs[1]["limit"] == 3


@pytest.mark.asyncio
async def test_autocomplete_limit_max_is_8(client):
    resp = await client.get("/api/v1/movies/autocomplete", params={"q": "a", "limit": 20})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_autocomplete_no_results(client, mock_movie_service):
    mock_movie_service.autocomplete.return_value = []
    resp = await client.get("/api/v1/movies/autocomplete", params={"q": "zzzzz"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["query"] == "zzzzz"


@pytest.mark.asyncio
async def test_autocomplete_uses_cache(client, mock_movie_service, mock_cache_service):
    import json

    cached_response = json.dumps({
        "results": [{"id": 99, "title": "Cached Movie", "year": 2020, "poster_path": None}],
        "query": "cached",
    })
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/autocomplete", params={"q": "cached"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["title"] == "Cached Movie"
    mock_movie_service.autocomplete.assert_not_awaited()
