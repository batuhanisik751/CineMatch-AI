"""Tests for advanced search endpoint."""

from __future__ import annotations


async def test_advanced_search_no_filters(client, sample_movie):
    resp = await client.get("/api/v1/movies/advanced-search")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["title"] == sample_movie.title
    assert data["results"][0]["vote_average"] == sample_movie.vote_average
    assert data["results"][0]["director"] == sample_movie.director
    assert data["offset"] == 0
    assert data["limit"] == 20


async def test_advanced_search_genre_filter(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/advanced-search", params={"genre": "Action"})
    assert resp.status_code == 200
    mock_movie_service.advanced_search.assert_called_once()
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["genre"] == "Action"


async def test_advanced_search_decade_filter(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/advanced-search", params={"decade": "2010s"})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["decade"] == "2010s"


async def test_advanced_search_invalid_decade(client):
    resp = await client.get("/api/v1/movies/advanced-search", params={"decade": "abc"})
    assert resp.status_code == 422


async def test_advanced_search_rating_range(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/advanced-search", params={"min_rating": 7.0, "max_rating": 9.0}
    )
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["min_rating"] == 7.0
    assert call_kwargs["max_rating"] == 9.0


async def test_advanced_search_invalid_rating(client):
    resp = await client.get("/api/v1/movies/advanced-search", params={"min_rating": 11})
    assert resp.status_code == 422


async def test_advanced_search_director_filter(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/advanced-search", params={"director": "Nolan"})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["director"] == "Nolan"


async def test_advanced_search_keyword_filter(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/advanced-search", params={"keyword": "dystopia"})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["keyword"] == "dystopia"


async def test_advanced_search_cast_filter(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/advanced-search", params={"cast": "DiCaprio"})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["cast_name"] == "DiCaprio"


async def test_advanced_search_multiple_filters(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/advanced-search",
        params={
            "genre": "Sci-Fi",
            "decade": "2010s",
            "min_rating": 7.0,
            "director": "Villeneuve",
            "keyword": "dystopia",
        },
    )
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["genre"] == "Sci-Fi"
    assert call_kwargs["decade"] == "2010s"
    assert call_kwargs["min_rating"] == 7.0
    assert call_kwargs["director"] == "Villeneuve"
    assert call_kwargs["keyword"] == "dystopia"


async def test_advanced_search_sort_by(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/advanced-search", params={"sort_by": "vote_average"}
    )
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["sort_by"] == "vote_average"


async def test_advanced_search_pagination(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/advanced-search", params={"offset": 20, "limit": 10}
    )
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.advanced_search.call_args.kwargs
    assert call_kwargs["offset"] == 20
    assert call_kwargs["limit"] == 10
    data = resp.json()
    assert data["offset"] == 20
    assert data["limit"] == 10


async def test_advanced_search_empty_results(client, mock_movie_service):
    mock_movie_service.advanced_search.return_value = ([], 0)
    resp = await client.get("/api/v1/movies/advanced-search", params={"genre": "Nonexistent"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["results"] == []


async def test_advanced_search_cached(client, mock_movie_service, mock_cache_service):
    import json

    cached_data = {
        "results": [],
        "total": 0,
        "offset": 0,
        "limit": 20,
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)
    resp = await client.get("/api/v1/movies/advanced-search", params={"genre": "Action"})
    assert resp.status_code == 200
    mock_movie_service.advanced_search.assert_not_called()
