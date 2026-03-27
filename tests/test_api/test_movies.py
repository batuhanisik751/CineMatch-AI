"""Tests for movie API endpoints."""

from __future__ import annotations


async def test_get_movie_success(client, sample_movie):
    resp = await client.get(f"/api/v1/movies/{sample_movie.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sample_movie.id
    assert data["title"] == sample_movie.title
    assert data["genres"] == sample_movie.genres


async def test_get_movie_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.get("/api/v1/movies/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Movie not found"


async def test_search_movies_success(client, sample_movie):
    resp = await client.get("/api/v1/movies/search", params={"q": "matrix"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "matrix"
    assert data["total"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == sample_movie.title


async def test_search_movies_empty_query(client):
    resp = await client.get("/api/v1/movies/search", params={"q": ""})
    assert resp.status_code == 422


async def test_search_movies_with_limit(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/search", params={"q": "test", "limit": 5})
    assert resp.status_code == 200
    mock_movie_service.search_by_title.assert_called_once()
    call_args = mock_movie_service.search_by_title.call_args
    assert call_args[1]["limit"] == 5 or call_args[0][2] == 5 or call_args.kwargs.get("limit") == 5


async def test_get_similar_movies_success(client, sample_movie, mock_movie_service):
    from tests.test_api.conftest import _make_movie

    movie2 = _make_movie(id=2, title="The Matrix Reloaded")
    movie3 = _make_movie(id=3, title="The Matrix Revolutions")

    mock_movie_service.get_movies_by_ids.return_value = {2: movie2, 3: movie3}

    resp = await client.get(f"/api/v1/movies/{sample_movie.id}/similar")
    assert resp.status_code == 200
    data = resp.json()
    assert data["movie_id"] == sample_movie.id
    assert len(data["similar"]) == 2
    assert data["similar"][0]["similarity"] == 0.92


async def test_get_similar_movies_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.get("/api/v1/movies/999/similar")
    assert resp.status_code == 404


async def test_get_similar_movies_service_unavailable(app, client):
    from cinematch.api.deps import get_content_recommender

    app.dependency_overrides[get_content_recommender] = lambda: None
    resp = await client.get("/api/v1/movies/1/similar")
    assert resp.status_code == 503
    assert "Content recommendation service" in resp.json()["detail"]
