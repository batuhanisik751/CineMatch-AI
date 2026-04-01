"""Tests for the Movie DNA endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio()
async def test_movie_dna_success(client: AsyncClient):
    resp = await client.get("/api/v1/movies/1/dna")
    assert resp.status_code == 200
    data = resp.json()
    assert data["movie_id"] == 1
    assert data["title"] == "The Matrix"
    assert len(data["genres"]) == 2
    assert data["genres"][0]["genre"] == "Action"
    assert data["decade"] == 1990
    assert len(data["mood_tags"]) == 2
    assert data["director"] == "Lana Wachowski"
    assert data["vote_average"] == 8.2
    assert len(data["top_keywords"]) == 2


@pytest.mark.asyncio()
async def test_movie_dna_not_found(client: AsyncClient, mock_movie_service):
    mock_movie_service.get_movie_dna.return_value = None
    resp = await client.get("/api/v1/movies/999/dna")
    assert resp.status_code == 404


@pytest.mark.asyncio()
async def test_movie_dna_service_unavailable(client: AsyncClient, app):
    from cinematch.api.deps import get_content_recommender

    app.dependency_overrides[get_content_recommender] = lambda: None
    resp = await client.get("/api/v1/movies/1/dna")
    assert resp.status_code == 503
