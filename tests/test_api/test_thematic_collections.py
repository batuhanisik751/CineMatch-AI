"""Tests for thematic collection endpoints."""

from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_list_collections_default(client, mock_thematic_collection_service):
    resp = await client.get("/api/v1/movies/thematic-collections")
    assert resp.status_code == 200
    data = resp.json()
    assert data["collection_type"] is None
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "genre_decade:Action:1990"
    assert data["results"][0]["title"] == "Best Action of the 1990s"
    mock_thematic_collection_service.list_collections.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_collections_with_type_filter(client, mock_thematic_collection_service):
    resp = await client.get("/api/v1/movies/thematic-collections?collection_type=director")
    assert resp.status_code == 200
    call_kwargs = mock_thematic_collection_service.list_collections.call_args
    assert call_kwargs.kwargs["collection_type"] == "director"


@pytest.mark.asyncio
async def test_list_collections_invalid_type(client):
    resp = await client.get("/api/v1/movies/thematic-collections?collection_type=invalid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_collection_detail(client, mock_thematic_collection_service):
    resp = await client.get("/api/v1/movies/thematic-collections/genre_decade:Action:1990")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "genre_decade:Action:1990"
    assert data["title"] == "Best Action of the 1990s"
    assert data["collection_type"] == "genre_decade"
    assert len(data["results"]) == 1
    assert data["results"][0]["avg_rating"] == 8.5
    assert data["results"][0]["rating_count"] == 150
    assert data["results"][0]["movie"]["title"] == "The Matrix"


@pytest.mark.asyncio
async def test_get_collection_not_found(client, mock_thematic_collection_service):
    mock_thematic_collection_service.get_collection.return_value = None
    resp = await client.get("/api/v1/movies/thematic-collections/unknown:bad:id")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Collection not found"


@pytest.mark.asyncio
async def test_get_collection_with_limit(client, mock_thematic_collection_service):
    resp = await client.get(
        "/api/v1/movies/thematic-collections/director:Christopher Nolan?limit=5"
    )
    assert resp.status_code == 200
    call_kwargs = mock_thematic_collection_service.get_collection.call_args
    assert call_kwargs.kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_list_collections_cache_hit(
    client, mock_thematic_collection_service, mock_cache_service
):
    cached_data = {
        "results": [
            {
                "id": "year:2020",
                "title": "Highest Rated 2020",
                "collection_type": "year",
                "movie_count": 50,
                "preview_posters": [],
            }
        ],
        "collection_type": "year",
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)

    resp = await client.get("/api/v1/movies/thematic-collections?collection_type=year")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["id"] == "year:2020"
    # Service should NOT have been called since we got a cache hit
    mock_thematic_collection_service.list_collections.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_collection_cache_hit(
    client, mock_thematic_collection_service, mock_cache_service
):
    cached_data = {
        "id": "director:Nolan",
        "title": "Nolan: A Filmography",
        "collection_type": "director",
        "results": [],
        "total": 0,
        "limit": 20,
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)

    resp = await client.get("/api/v1/movies/thematic-collections/director:Nolan")
    assert resp.status_code == 200
    assert resp.json()["id"] == "director:Nolan"
    mock_thematic_collection_service.get_collection.assert_not_awaited()
