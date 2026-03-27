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


# --- Discover endpoint tests ---


async def test_discover_no_filters(client):
    resp = await client.get("/api/v1/movies/discover")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "total" in data
    assert data["offset"] == 0
    assert data["limit"] == 20


async def test_discover_with_genre(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/discover", params={"genre": "Action"})
    assert resp.status_code == 200
    mock_movie_service.list_movies.assert_called_once()
    call_kwargs = mock_movie_service.list_movies.call_args.kwargs
    assert call_kwargs["genre"] == "Action"


async def test_discover_with_year_range(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/discover", params={"year_min": 2000, "year_max": 2020})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.list_movies.call_args.kwargs
    assert call_kwargs["year_min"] == 2000
    assert call_kwargs["year_max"] == 2020


async def test_discover_with_sort(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/discover", params={"sort_by": "vote_average"})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.list_movies.call_args.kwargs
    assert call_kwargs["sort_by"] == "vote_average"


async def test_discover_with_pagination(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/discover", params={"offset": 20, "limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["offset"] == 20
    assert data["limit"] == 10
    call_kwargs = mock_movie_service.list_movies.call_args.kwargs
    assert call_kwargs["offset"] == 20
    assert call_kwargs["limit"] == 10


async def test_discover_invalid_sort(client):
    resp = await client.get("/api/v1/movies/discover", params={"sort_by": "invalid"})
    assert resp.status_code == 422


async def test_discover_invalid_limit(client):
    resp = await client.get("/api/v1/movies/discover", params={"limit": 0})
    assert resp.status_code == 422


# --- Genres endpoint tests ---


async def test_genres_success(client):
    resp = await client.get("/api/v1/movies/genres")
    assert resp.status_code == 200
    data = resp.json()
    assert "genres" in data
    assert len(data["genres"]) == 2


async def test_genres_response_structure(client):
    resp = await client.get("/api/v1/movies/genres")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["genres"]:
        assert "genre" in item
        assert "count" in item
        assert isinstance(item["count"], int)
    assert data["genres"][0]["genre"] == "Action"
    assert data["genres"][0]["count"] == 50


# --- Semantic search endpoint tests ---


async def test_semantic_search_success(client, sample_movie, mock_movie_service):
    mock_movie_service.semantic_search.return_value = [(sample_movie, 0.91)]

    resp = await client.get(
        "/api/v1/movies/semantic-search", params={"q": "dark thriller in space"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "dark thriller in space"
    assert data["total"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["title"] == sample_movie.title
    assert data["results"][0]["similarity"] == 0.91


async def test_semantic_search_empty_query(client):
    resp = await client.get("/api/v1/movies/semantic-search", params={"q": ""})
    assert resp.status_code == 422


async def test_semantic_search_service_unavailable(app, client):
    from cinematch.api.deps import get_embedding_service

    app.dependency_overrides[get_embedding_service] = lambda: None
    resp = await client.get("/api/v1/movies/semantic-search", params={"q": "funny movie"})
    assert resp.status_code == 503
    assert "Embedding service" in resp.json()["detail"]


async def test_semantic_search_no_results(client, mock_movie_service):
    mock_movie_service.semantic_search.return_value = []

    resp = await client.get(
        "/api/v1/movies/semantic-search", params={"q": "completely unknown vibe"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["results"] == []
