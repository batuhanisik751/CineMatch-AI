"""Tests for GET /api/v1/movies/controversial endpoint."""

from __future__ import annotations


async def test_controversial_endpoint_200(client, sample_movie):
    resp = await client.get("/api/v1/movies/controversial")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["min_ratings"] == 100
    assert data["limit"] == 20
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["movie"]["id"] == sample_movie.id
    assert result["avg_rating"] == 7.3
    assert result["stddev_rating"] == 2.15
    assert result["rating_count"] == 150
    assert len(result["histogram"]) == 10
    assert result["histogram"][0]["rating"] == 1


async def test_controversial_custom_params(client):
    resp = await client.get("/api/v1/movies/controversial", params={"min_ratings": 50, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_ratings"] == 50
    assert data["limit"] == 5


async def test_controversial_uses_cache(client, mock_cache_service, mock_movie_service):
    cached_json = (
        '{"results":[{"movie":{"id":1,"title":"Cached","genres":[],'
        '"vote_average":7.0,"release_date":null,"poster_path":null},'
        '"avg_rating":6.5,"stddev_rating":2.0,"rating_count":200,'
        '"histogram":[{"rating":1,"count":20},{"rating":2,"count":20},'
        '{"rating":3,"count":20},{"rating":4,"count":20},{"rating":5,"count":20},'
        '{"rating":6,"count":20},{"rating":7,"count":20},{"rating":8,"count":20},'
        '{"rating":9,"count":20},{"rating":10,"count":20}]}],'
        '"min_ratings":100,"limit":20}'
    )
    mock_cache_service.get.return_value = cached_json

    resp = await client.get("/api/v1/movies/controversial")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["movie"]["title"] == "Cached"
    # Service should NOT have been called
    mock_movie_service.controversial.assert_not_called()


async def test_controversial_validation_min_ratings_too_low(client):
    resp = await client.get("/api/v1/movies/controversial", params={"min_ratings": 5})
    assert resp.status_code == 422


async def test_controversial_validation_limit_too_high(client):
    resp = await client.get("/api/v1/movies/controversial", params={"limit": 200})
    assert resp.status_code == 422
