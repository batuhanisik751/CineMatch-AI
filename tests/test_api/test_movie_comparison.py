"""Tests for movie comparison endpoint."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_compare_returns_200_with_valid_ids(client):
    resp = await client.get("/api/v1/movies/compare?ids=1,2")
    assert resp.status_code == 200
    data = resp.json()
    assert "movie1" in data
    assert "movie2" in data
    assert "shared_genres" in data
    assert "shared_actors" in data
    assert "shared_keywords" in data
    assert "same_director" in data
    assert "embedding_similarity" in data
    assert "rating_comparison" in data
    assert data["als_prediction"] is None


@pytest.mark.asyncio
async def test_compare_includes_shared_attributes(client, mock_movie_service):
    from datetime import date
    from unittest.mock import MagicMock

    movie1 = MagicMock()
    movie1.id = 1
    movie1.tmdb_id = 603
    movie1.imdb_id = "tt0133093"
    movie1.title = "The Matrix"
    movie1.overview = "A simulation."
    movie1.genres = ["Action", "Sci-Fi"]
    movie1.keywords = ["hacker", "simulation"]
    movie1.cast_names = ["Keanu Reeves", "Carrie-Anne Moss"]
    movie1.director = "Lana Wachowski"
    movie1.release_date = date(1999, 3, 31)
    movie1.vote_average = 8.2
    movie1.vote_count = 20000
    movie1.popularity = 50.0
    movie1.poster_path = "/poster.jpg"
    movie1.original_language = "en"
    movie1.runtime = 136

    movie2 = MagicMock()
    movie2.id = 2
    movie2.tmdb_id = 604
    movie2.imdb_id = "tt0234215"
    movie2.title = "The Matrix Reloaded"
    movie2.overview = "Neo continues."
    movie2.genres = ["Action", "Thriller"]
    movie2.keywords = ["hacker", "prophecy"]
    movie2.cast_names = ["Keanu Reeves", "Laurence Fishburne"]
    movie2.director = "Lana Wachowski"
    movie2.release_date = date(2003, 5, 15)
    movie2.vote_average = 6.7
    movie2.vote_count = 15000
    movie2.popularity = 40.0
    movie2.poster_path = "/poster2.jpg"
    movie2.original_language = "en"
    movie2.runtime = 138

    async def side_effect(mid, db):
        if mid == 1:
            return movie1
        if mid == 2:
            return movie2
        return None

    mock_movie_service.get_by_id.side_effect = side_effect

    resp = await client.get("/api/v1/movies/compare?ids=1,2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["shared_genres"] == ["Action"]
    assert data["shared_actors"] == ["Keanu Reeves"]
    assert data["shared_keywords"] == ["hacker"]
    assert data["same_director"] is True


@pytest.mark.asyncio
async def test_compare_404_when_movie_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.get("/api/v1/movies/compare?ids=1,999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compare_400_single_id(client):
    resp = await client.get("/api/v1/movies/compare?ids=1")
    assert resp.status_code == 400
    assert "two" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_compare_400_same_ids(client):
    resp = await client.get("/api/v1/movies/compare?ids=1,1")
    assert resp.status_code == 400
    assert "different" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_compare_400_non_numeric(client):
    resp = await client.get("/api/v1/movies/compare?ids=abc,def")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_compare_with_user_id_includes_als(client, mock_collab_recommender):
    mock_collab_recommender.score_items.return_value = {1: 0.72, 2: 0.65}
    resp = await client.get("/api/v1/movies/compare?ids=1,2&user_id=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["als_prediction"] is not None
    assert data["als_prediction"]["user_id"] == 1
    assert data["als_prediction"]["preferred_movie_id"] == 1


@pytest.mark.asyncio
async def test_compare_without_user_id_no_als(client):
    resp = await client.get("/api/v1/movies/compare?ids=1,2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["als_prediction"] is None
