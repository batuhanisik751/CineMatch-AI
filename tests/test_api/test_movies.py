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


# --- Languages endpoint tests ---


async def test_languages_success(client):
    resp = await client.get("/api/v1/movies/languages")
    assert resp.status_code == 200
    data = resp.json()
    assert "languages" in data
    assert len(data["languages"]) == 3


async def test_languages_response_structure(client):
    resp = await client.get("/api/v1/movies/languages")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["languages"]:
        assert "code" in item
        assert "name" in item
        assert "count" in item
        assert isinstance(item["count"], int)
    assert data["languages"][0]["code"] == "en"
    assert data["languages"][0]["count"] == 8000


# --- Discover with language filter ---


async def test_discover_with_language(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/discover", params={"language": "ko"})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.list_movies.call_args.kwargs
    assert call_kwargs["language"] == "ko"


async def test_discover_with_runtime_range(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/discover", params={"min_runtime": 90, "max_runtime": 150}
    )
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.list_movies.call_args.kwargs
    assert call_kwargs["min_runtime"] == 90
    assert call_kwargs["max_runtime"] == 150


async def test_discover_with_min_runtime_only(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/discover", params={"min_runtime": 120})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.list_movies.call_args.kwargs
    assert call_kwargs["min_runtime"] == 120
    assert call_kwargs["max_runtime"] is None


async def test_discover_invalid_runtime(client):
    resp = await client.get("/api/v1/movies/discover", params={"min_runtime": 0})
    assert resp.status_code == 422


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


# --- Trending endpoint tests ---


async def test_trending_default_params(client, sample_movie):
    resp = await client.get("/api/v1/movies/trending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["window"] == 7
    assert data["limit"] == 20
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["title"] == sample_movie.title
    assert data["results"][0]["rating_count"] == 42


async def test_trending_custom_params(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/trending", params={"window": 30, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["window"] == 30
    assert data["limit"] == 5
    mock_movie_service.trending.assert_called_once()
    call_kwargs = mock_movie_service.trending.call_args.kwargs
    assert call_kwargs["window"] == 30
    assert call_kwargs["limit"] == 5


async def test_trending_cache_miss(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/trending")
    assert resp.status_code == 200
    mock_movie_service.trending.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "trending:7:20"
    assert call_args[1]["ttl"] == 3600


async def test_trending_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = (
        '{"results":[{"movie":{"id":1,"title":"The Matrix","genres":["Action","Sci-Fi"],'
        '"vote_average":8.2,"release_date":"1999-03-31","poster_path":"/poster.jpg"},'
        '"rating_count":42}],"window":7,"limit":20}'
    )
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/trending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["movie"]["title"] == "The Matrix"
    mock_movie_service.trending.assert_not_called()


async def test_trending_invalid_window(client):
    resp = await client.get("/api/v1/movies/trending", params={"window": 0})
    assert resp.status_code == 422

    resp = await client.get("/api/v1/movies/trending", params={"window": 91})
    assert resp.status_code == 422


async def test_trending_invalid_limit(client):
    resp = await client.get("/api/v1/movies/trending", params={"limit": 0})
    assert resp.status_code == 422

    resp = await client.get("/api/v1/movies/trending", params={"limit": 101})
    assert resp.status_code == 422


async def test_trending_no_cache_service(app, client, mock_movie_service):
    from cinematch.api.deps import get_cache_service

    app.dependency_overrides[get_cache_service] = lambda: None
    resp = await client.get("/api/v1/movies/trending")
    assert resp.status_code == 200
    mock_movie_service.trending.assert_called_once()


async def test_trending_exclude_rated_filters_results(
    client, mock_movie_service, mock_rating_service, sample_movie
):
    from tests.test_api.conftest import _make_movie

    movie2 = _make_movie(id=2, title="Inception")
    mock_movie_service.trending.return_value = [(sample_movie, 42), (movie2, 30)]
    mock_rating_service.get_rated_movie_ids.return_value = {1}  # sample_movie.id == 1

    resp = await client.get(
        "/api/v1/movies/trending",
        params={"user_id": 1, "exclude_rated": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Movie 1 (The Matrix) should be filtered out, only Inception remains
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["title"] == "Inception"


async def test_trending_without_exclude_rated_returns_all(client, mock_movie_service, sample_movie):
    resp = await client.get("/api/v1/movies/trending")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1


# --- Hidden Gems endpoint tests ---


async def test_hidden_gems_default_params(client, sample_movie):
    resp = await client.get("/api/v1/movies/hidden-gems")
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_rating"] == 7.5
    assert data["max_votes"] == 100
    assert data["limit"] == 20
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["title"] == sample_movie.title
    assert data["results"][0]["vote_average"] == sample_movie.vote_average
    assert data["results"][0]["vote_count"] == sample_movie.vote_count


async def test_hidden_gems_custom_params(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/hidden-gems",
        params={"min_rating": 8.0, "max_votes": 50, "genre": "Drama", "limit": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_rating"] == 8.0
    assert data["max_votes"] == 50
    assert data["limit"] == 10
    mock_movie_service.hidden_gems.assert_called_once()
    call_kwargs = mock_movie_service.hidden_gems.call_args.kwargs
    assert call_kwargs["min_rating"] == 8.0
    assert call_kwargs["max_votes"] == 50
    assert call_kwargs["genre"] == "Drama"
    assert call_kwargs["limit"] == 10


async def test_hidden_gems_cache_miss(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/hidden-gems")
    assert resp.status_code == 200
    mock_movie_service.hidden_gems.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "hidden_gems:7.5:100:None:20"  # min_rating rounded to 1dp
    assert call_args[1]["ttl"] == 21600


async def test_hidden_gems_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = (
        '{"results":[{"movie":{"id":1,"title":"The Matrix","genres":["Action","Sci-Fi"],'
        '"vote_average":8.2,"release_date":"1999-03-31","poster_path":"/poster.jpg"},'
        '"vote_average":8.2,"vote_count":20000}],"min_rating":7.5,"max_votes":100,"limit":20}'
    )
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/hidden-gems")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["movie"]["title"] == "The Matrix"
    mock_movie_service.hidden_gems.assert_not_called()


async def test_hidden_gems_invalid_min_rating(client):
    resp = await client.get("/api/v1/movies/hidden-gems", params={"min_rating": 11})
    assert resp.status_code == 422


async def test_hidden_gems_invalid_max_votes(client):
    resp = await client.get("/api/v1/movies/hidden-gems", params={"max_votes": 0})
    assert resp.status_code == 422


async def test_hidden_gems_invalid_limit(client):
    resp = await client.get("/api/v1/movies/hidden-gems", params={"limit": 0})
    assert resp.status_code == 422

    resp = await client.get("/api/v1/movies/hidden-gems", params={"limit": 101})
    assert resp.status_code == 422


async def test_hidden_gems_no_cache_service(app, client, mock_movie_service):
    from cinematch.api.deps import get_cache_service

    app.dependency_overrides[get_cache_service] = lambda: None
    resp = await client.get("/api/v1/movies/hidden-gems")
    assert resp.status_code == 200
    mock_movie_service.hidden_gems.assert_called_once()


# --- Top Charts by Genre endpoint tests ---


async def test_top_charts_success(client, sample_movie):
    resp = await client.get("/api/v1/movies/top", params={"genre": "Thriller"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["genre"] == "Thriller"
    assert data["limit"] == 20
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["movie"]["title"] == sample_movie.title
    assert result["avg_rating"] == 8.5
    assert result["rating_count"] == 150


async def test_top_charts_missing_genre_returns_422(client):
    resp = await client.get("/api/v1/movies/top")
    assert resp.status_code == 422


async def test_top_charts_custom_limit(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/top", params={"genre": "Action", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 5
    call_kwargs = mock_movie_service.top_by_genre.call_args.kwargs
    assert call_kwargs["limit"] == 5


async def test_top_charts_cache_miss(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/top", params={"genre": "Thriller"})
    assert resp.status_code == 200
    mock_movie_service.top_by_genre.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "top_charts:Thriller:20"
    assert call_args[1]["ttl"] == 21600


async def test_top_charts_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = (
        '{"results":[{"movie":{"id":1,"title":"The Matrix","genres":["Action","Sci-Fi"],'
        '"vote_average":8.2,"release_date":"1999-03-31","poster_path":"/poster.jpg"},'
        '"avg_rating":8.5,"rating_count":150}],"genre":"Thriller","limit":20}'
    )
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/top", params={"genre": "Thriller"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["movie"]["title"] == "The Matrix"
    mock_movie_service.top_by_genre.assert_not_called()


async def test_top_charts_invalid_limit_zero(client):
    resp = await client.get("/api/v1/movies/top", params={"genre": "Action", "limit": 0})
    assert resp.status_code == 422


async def test_top_charts_invalid_limit_over_max(client):
    resp = await client.get("/api/v1/movies/top", params={"genre": "Action", "limit": 101})
    assert resp.status_code == 422


async def test_top_charts_no_cache_service(app, client, mock_movie_service):
    from cinematch.api.deps import get_cache_service

    app.dependency_overrides[get_cache_service] = lambda: None
    resp = await client.get("/api/v1/movies/top", params={"genre": "Drama"})
    assert resp.status_code == 200
    mock_movie_service.top_by_genre.assert_called_once()


async def test_top_charts_empty_results(client, mock_movie_service):
    mock_movie_service.top_by_genre.return_value = []
    resp = await client.get("/api/v1/movies/top", params={"genre": "Horror"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["genre"] == "Horror"


# --- Decades ---


async def test_decades_success(client):
    resp = await client.get("/api/v1/movies/decades")
    assert resp.status_code == 200
    data = resp.json()
    assert "decades" in data
    assert len(data["decades"]) == 2


async def test_decades_response_structure(client):
    resp = await client.get("/api/v1/movies/decades")
    data = resp.json()
    item = data["decades"][0]
    assert item["decade"] == 2000
    assert item["movie_count"] == 150
    assert item["avg_rating"] == 6.8


async def test_decades_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = '{"decades":[{"decade":2000,"movie_count":150,"avg_rating":6.8}]}'
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/decades")
    assert resp.status_code == 200
    data = resp.json()
    assert data["decades"][0]["decade"] == 2000
    mock_movie_service.get_decade_stats.assert_not_called()


async def test_decades_cache_miss(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/decades")
    assert resp.status_code == 200
    mock_movie_service.get_decade_stats.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "decades"
    assert call_args[1]["ttl"] == 21600


async def test_decades_no_cache_service(app, client, mock_movie_service):
    from cinematch.api.deps import get_cache_service

    app.dependency_overrides[get_cache_service] = lambda: None
    resp = await client.get("/api/v1/movies/decades")
    assert resp.status_code == 200
    mock_movie_service.get_decade_stats.assert_called_once()


# --- Decade Movies ---


async def test_decade_movies_default_params(client, sample_movie):
    resp = await client.get("/api/v1/movies/decades/1990")
    assert resp.status_code == 200
    data = resp.json()
    assert data["decade"] == 1990
    assert data["offset"] == 0
    assert data["limit"] == 20
    assert data["total"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["id"] == sample_movie.id


async def test_decade_movies_with_genre(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/decades/1990", params={"genre": "Action"})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.top_by_decade.call_args.kwargs
    assert call_kwargs["genre"] == "Action"


async def test_decade_movies_with_pagination(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/decades/2000", params={"offset": 20, "limit": 10})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.top_by_decade.call_args.kwargs
    assert call_kwargs["offset"] == 20
    assert call_kwargs["limit"] == 10


async def test_decade_movies_invalid_decade(client):
    resp = await client.get("/api/v1/movies/decades/1995")
    assert resp.status_code == 400
    assert "Invalid decade" in resp.json()["detail"]


async def test_decade_movies_invalid_decade_out_of_range(client):
    resp = await client.get("/api/v1/movies/decades/1800")
    assert resp.status_code == 400


async def test_decade_movies_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = (
        '{"results":[{"movie":{"id":1,"title":"The Matrix","genres":["Action","Sci-Fi"],'
        '"vote_average":8.2,"release_date":"1999-03-31","poster_path":"/poster.jpg"},'
        '"avg_rating":8.5,"rating_count":150}],"decade":1990,"genre":null,'
        '"total":1,"offset":0,"limit":20}'
    )
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/decades/1990")
    assert resp.status_code == 200
    mock_movie_service.top_by_decade.assert_not_called()


async def test_decade_movies_cache_miss(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/decades/1990")
    assert resp.status_code == 200
    mock_movie_service.top_by_decade.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "decade_movies:1990:None:0:20"
    assert call_args[1]["ttl"] == 21600


async def test_decade_movies_empty_results(client, mock_movie_service):
    mock_movie_service.top_by_decade.return_value = ([], 0)
    resp = await client.get("/api/v1/movies/decades/1920")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["total"] == 0


# --- Director Spotlight ---


async def test_directors_search_success(client):
    resp = await client.get("/api/v1/movies/directors/search", params={"q": "nolan"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "nolan"
    assert len(data["results"]) == 1
    assert data["results"][0]["name"] == "Christopher Nolan"
    assert data["results"][0]["film_count"] == 12
    assert data["results"][0]["avg_vote"] == 7.84


async def test_directors_search_empty_query_422(client):
    resp = await client.get("/api/v1/movies/directors/search", params={"q": ""})
    assert resp.status_code == 422


async def test_directors_search_custom_limit(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/directors/search", params={"q": "spielberg", "limit": 5}
    )
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.search_directors.call_args
    assert call_kwargs[1]["limit"] == 5 or call_kwargs.kwargs.get("limit") == 5


async def test_directors_popular_success(client):
    resp = await client.get("/api/v1/movies/directors/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 30
    assert len(data["results"]) == 2
    assert data["results"][0]["name"] == "Christopher Nolan"
    assert data["results"][1]["name"] == "Steven Spielberg"


async def test_directors_popular_cache_miss(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/directors/popular")
    assert resp.status_code == 200
    mock_movie_service.popular_directors.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "popular_directors:30"
    assert call_args[1]["ttl"] == 21600


async def test_directors_popular_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = (
        '{"results":[{"name":"Christopher Nolan","film_count":12,"avg_vote":7.84}],"limit":30}'
    )
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/directors/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["name"] == "Christopher Nolan"
    mock_movie_service.popular_directors.assert_not_called()


async def test_directors_filmography_success(client, sample_movie):
    resp = await client.get(
        "/api/v1/movies/directors/filmography", params={"name": "Lana Wachowski"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["director"] == "Lana Wachowski"
    assert data["stats"]["total_films"] == 1
    assert data["stats"]["avg_vote"] == 8.2
    assert "Action" in data["stats"]["genres"]
    assert data["stats"]["user_avg_rating"] is None
    assert data["stats"]["user_rated_count"] == 0
    assert len(data["filmography"]) == 1
    assert data["filmography"][0]["movie"]["title"] == sample_movie.title
    assert data["filmography"][0]["user_rating"] is None


async def test_directors_filmography_with_user_id(client, mock_movie_service, sample_movie):
    mock_movie_service.filmography_by_director.return_value = (
        [(sample_movie, 9.0)],
        {
            "total_films": 1,
            "avg_vote": 8.2,
            "genres": ["Action", "Sci-Fi"],
            "user_avg_rating": 9.0,
            "user_rated_count": 1,
        },
    )

    resp = await client.get(
        "/api/v1/movies/directors/filmography",
        params={"name": "Lana Wachowski", "user_id": 42},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filmography"][0]["user_rating"] == 9.0
    assert data["stats"]["user_avg_rating"] == 9.0
    assert data["stats"]["user_rated_count"] == 1

    call_kwargs = mock_movie_service.filmography_by_director.call_args.kwargs
    assert call_kwargs["user_id"] == 42


async def test_directors_filmography_no_cache_with_user_id(
    client, mock_movie_service, mock_cache_service
):
    resp = await client.get(
        "/api/v1/movies/directors/filmography",
        params={"name": "Lana Wachowski", "user_id": 42},
    )
    assert resp.status_code == 200
    # Cache set should not be called when user_id is provided
    mock_cache_service.set.assert_not_called()


async def test_directors_filmography_cache_miss_without_user_id(
    client, mock_movie_service, mock_cache_service
):
    resp = await client.get(
        "/api/v1/movies/directors/filmography", params={"name": "Lana Wachowski"}
    )
    assert resp.status_code == 200
    mock_movie_service.filmography_by_director.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "director_filmography:lana wachowski"
    assert call_args[1]["ttl"] == 21600


async def test_directors_filmography_missing_name_422(client):
    resp = await client.get("/api/v1/movies/directors/filmography")
    assert resp.status_code == 422


async def test_directors_filmography_not_found(client, mock_movie_service):
    mock_movie_service.filmography_by_director.return_value = (
        [],
        {
            "total_films": 0,
            "avg_vote": 0.0,
            "genres": [],
            "user_avg_rating": None,
            "user_rated_count": 0,
        },
    )
    resp = await client.get(
        "/api/v1/movies/directors/filmography", params={"name": "Nobody Unknown"}
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Director not found"


# --- Actor Filmography ---


async def test_actors_search_success(client):
    resp = await client.get("/api/v1/movies/actors/search", params={"q": "keanu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "keanu"
    assert len(data["results"]) == 1
    assert data["results"][0]["name"] == "Keanu Reeves"
    assert data["results"][0]["film_count"] == 8
    assert data["results"][0]["avg_vote"] == 7.15


async def test_actors_search_empty_query_422(client):
    resp = await client.get("/api/v1/movies/actors/search", params={"q": ""})
    assert resp.status_code == 422


async def test_actors_search_custom_limit(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/actors/search", params={"q": "tom", "limit": 5})
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.search_actors.call_args
    assert call_kwargs[1]["limit"] == 5 or call_kwargs.kwargs.get("limit") == 5


async def test_actors_popular_success(client):
    resp = await client.get("/api/v1/movies/actors/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 30
    assert len(data["results"]) == 2
    assert data["results"][0]["name"] == "Keanu Reeves"
    assert data["results"][1]["name"] == "Tom Hanks"


async def test_actors_popular_cache_miss(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/actors/popular")
    assert resp.status_code == 200
    mock_movie_service.popular_actors.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "popular_actors:30"
    assert call_args[1]["ttl"] == 21600


async def test_actors_popular_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = (
        '{"results":[{"name":"Keanu Reeves","film_count":8,"avg_vote":7.15}],"limit":30}'
    )
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/actors/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["name"] == "Keanu Reeves"
    mock_movie_service.popular_actors.assert_not_called()


async def test_actors_filmography_success(client, sample_movie):
    resp = await client.get("/api/v1/movies/actors/filmography", params={"name": "Keanu Reeves"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["actor"] == "Keanu Reeves"
    assert data["stats"]["total_films"] == 1
    assert data["stats"]["avg_vote"] == 8.2
    assert "Action" in data["stats"]["genres"]
    assert data["stats"]["user_avg_rating"] is None
    assert data["stats"]["user_rated_count"] == 0
    assert len(data["filmography"]) == 1
    assert data["filmography"][0]["movie"]["title"] == sample_movie.title
    assert data["filmography"][0]["user_rating"] is None


async def test_actors_filmography_with_user_id(client, mock_movie_service, sample_movie):
    mock_movie_service.filmography_by_actor.return_value = (
        [(sample_movie, 9.0)],
        {
            "total_films": 1,
            "avg_vote": 8.2,
            "genres": ["Action", "Sci-Fi"],
            "user_avg_rating": 9.0,
            "user_rated_count": 1,
        },
    )

    resp = await client.get(
        "/api/v1/movies/actors/filmography",
        params={"name": "Keanu Reeves", "user_id": 42},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filmography"][0]["user_rating"] == 9.0
    assert data["stats"]["user_avg_rating"] == 9.0
    assert data["stats"]["user_rated_count"] == 1

    call_kwargs = mock_movie_service.filmography_by_actor.call_args.kwargs
    assert call_kwargs["user_id"] == 42


async def test_actors_filmography_no_cache_with_user_id(
    client, mock_movie_service, mock_cache_service
):
    resp = await client.get(
        "/api/v1/movies/actors/filmography",
        params={"name": "Keanu Reeves", "user_id": 42},
    )
    assert resp.status_code == 200
    # Cache set should not be called when user_id is provided
    mock_cache_service.set.assert_not_called()


async def test_actors_filmography_cache_miss_without_user_id(
    client, mock_movie_service, mock_cache_service
):
    resp = await client.get("/api/v1/movies/actors/filmography", params={"name": "Keanu Reeves"})
    assert resp.status_code == 200
    mock_movie_service.filmography_by_actor.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "actor_filmography:keanu reeves"
    assert call_args[1]["ttl"] == 21600


async def test_actors_filmography_missing_name_422(client):
    resp = await client.get("/api/v1/movies/actors/filmography")
    assert resp.status_code == 422


async def test_actors_filmography_not_found(client, mock_movie_service):
    mock_movie_service.filmography_by_actor.return_value = (
        [],
        {
            "total_films": 0,
            "avg_vote": 0.0,
            "genres": [],
            "user_avg_rating": None,
            "user_rated_count": 0,
        },
    )
    resp = await client.get("/api/v1/movies/actors/filmography", params={"name": "Nobody Unknown"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Actor not found"


# --- Keyword Tag Cloud ---


async def test_popular_keywords_success(client):
    resp = await client.get("/api/v1/movies/keywords/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 50
    assert len(data["results"]) == 2
    assert data["results"][0]["keyword"] == "time travel"
    assert data["results"][0]["count"] == 42
    assert data["results"][1]["keyword"] == "dystopia"


async def test_popular_keywords_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = '{"results":[{"keyword":"time travel","count":42}],"limit":50}'
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/keywords/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["keyword"] == "time travel"
    mock_movie_service.popular_keywords.assert_not_called()


async def test_popular_keywords_cache_miss(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/keywords/popular")
    assert resp.status_code == 200
    mock_movie_service.popular_keywords.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "popular_keywords:50"
    assert call_args[1]["ttl"] == 21600


async def test_search_keywords_success(client):
    resp = await client.get("/api/v1/movies/keywords/search", params={"q": "time"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "time"
    assert len(data["results"]) == 1
    assert data["results"][0]["keyword"] == "time travel"
    assert data["results"][0]["count"] == 42


async def test_search_keywords_empty_query_422(client):
    resp = await client.get("/api/v1/movies/keywords/search", params={"q": ""})
    assert resp.status_code == 422


async def test_keyword_movies_success(client, sample_movie):
    resp = await client.get("/api/v1/movies/keywords/movies", params={"keyword": "time travel"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["keyword"] == "time travel"
    assert data["total"] == 1
    assert data["offset"] == 0
    assert data["limit"] == 20
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["id"] == sample_movie.id
    assert data["stats"]["total_movies"] == 1
    assert data["stats"]["avg_vote"] == 8.2
    assert "Action" in data["stats"]["top_genres"]


async def test_keyword_movies_pagination(client, mock_movie_service):
    resp = await client.get(
        "/api/v1/movies/keywords/movies",
        params={"keyword": "dystopia", "offset": 20, "limit": 10},
    )
    assert resp.status_code == 200
    call_kwargs = mock_movie_service.movies_by_keyword.call_args.kwargs
    assert call_kwargs["offset"] == 20
    assert call_kwargs["limit"] == 10


# --- Movie Activity Timeline tests ---


async def test_movie_activity_success(client, sample_movie):
    resp = await client.get(f"/api/v1/movies/{sample_movie.id}/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["movie_id"] == sample_movie.id
    assert data["granularity"] == "month"
    assert len(data["timeline"]) == 2
    assert data["total_ratings"] == 37
    assert data["timeline"][0]["period"] == "2024-01"
    assert data["timeline"][0]["rating_count"] == 15


async def test_movie_activity_week_granularity(client, sample_movie, mock_rating_service):
    mock_rating_service.get_movie_activity.return_value = {
        "movie_id": sample_movie.id,
        "granularity": "week",
        "timeline": [{"period": "2024-W01", "rating_count": 5, "avg_rating": 7.0}],
        "total_ratings": 5,
    }
    resp = await client.get(
        f"/api/v1/movies/{sample_movie.id}/activity", params={"granularity": "week"}
    )
    assert resp.status_code == 200
    assert resp.json()["granularity"] == "week"


async def test_movie_activity_invalid_granularity(client, sample_movie):
    resp = await client.get(
        f"/api/v1/movies/{sample_movie.id}/activity", params={"granularity": "year"}
    )
    assert resp.status_code == 422


async def test_movie_activity_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.get("/api/v1/movies/999/activity")
    assert resp.status_code == 404


# --- seasonal endpoint tests ---


async def test_seasonal_default_params(client, sample_movie):
    resp = await client.get("/api/v1/movies/seasonal")
    assert resp.status_code == 200
    data = resp.json()
    assert "season_name" in data
    assert "theme_label" in data
    assert "month" in data
    assert data["limit"] == 20
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["title"] == sample_movie.title


async def test_seasonal_custom_month(client, mock_movie_service):
    resp = await client.get("/api/v1/movies/seasonal", params={"month": 10, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 5
    mock_movie_service.seasonal.assert_called_once()
    call_kwargs = mock_movie_service.seasonal.call_args.kwargs
    assert call_kwargs["month"] == 10
    assert call_kwargs["limit"] == 5


async def test_seasonal_cache_miss_and_set(client, mock_movie_service, mock_cache_service):
    resp = await client.get("/api/v1/movies/seasonal", params={"month": 10})
    assert resp.status_code == 200
    mock_movie_service.seasonal.assert_called_once()
    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "seasonal:10:20"
    assert call_args[1]["ttl"] == 21600


async def test_seasonal_cache_hit(client, mock_movie_service, mock_cache_service):
    cached_response = (
        '{"results":[{"movie":{"id":1,"title":"The Matrix","genres":["Action","Sci-Fi"],'
        '"vote_average":8.2,"release_date":"1999-03-31","poster_path":"/poster.jpg"},'
        '"vote_average":8.2,"popularity":50.0}],'
        '"season_name":"Spooky Season","theme_label":"Halloween Frights",'
        '"month":10,"genres":["Horror","Thriller"],'
        '"keywords":["horror","halloween"],"limit":20}'
    )
    mock_cache_service.get.return_value = cached_response

    resp = await client.get("/api/v1/movies/seasonal", params={"month": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["season_name"] == "Spooky Season"
    mock_movie_service.seasonal.assert_not_called()


async def test_seasonal_invalid_month(client):
    resp = await client.get("/api/v1/movies/seasonal", params={"month": 0})
    assert resp.status_code == 422

    resp = await client.get("/api/v1/movies/seasonal", params={"month": 13})
    assert resp.status_code == 422


async def test_seasonal_exclude_rated(
    client, mock_movie_service, mock_rating_service, sample_movie
):
    from tests.test_api.conftest import _make_movie

    movie2 = _make_movie(id=2, title="Scream")
    from unittest.mock import MagicMock

    mock_movie_service.seasonal.return_value = (
        [sample_movie, movie2],
        MagicMock(
            season_name="Spooky Season",
            theme_label="Halloween Frights",
            genres=["Horror"],
            keywords=["horror"],
        ),
    )
    mock_rating_service.get_rated_movie_ids.return_value = {sample_movie.id}

    resp = await client.get(
        "/api/v1/movies/seasonal",
        params={"month": 10, "user_id": 1, "exclude_rated": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["movie"]["title"] == "Scream"
