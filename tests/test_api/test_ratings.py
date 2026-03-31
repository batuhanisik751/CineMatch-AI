"""Tests for rating API endpoints."""

from __future__ import annotations


async def test_add_rating_success(client, sample_rating):
    resp = await client.post(
        "/api/v1/users/1/ratings",
        json={"movie_id": 1, "rating": 9},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == sample_rating.user_id
    assert data["movie_id"] == sample_rating.movie_id
    assert data["rating"] == sample_rating.rating
    assert data["movie_title"] == "The Matrix"


async def test_add_rating_movie_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.post(
        "/api/v1/users/1/ratings",
        json={"movie_id": 999, "rating": 8},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Movie not found"


async def test_add_rating_invalid_value(client):
    resp = await client.post(
        "/api/v1/users/1/ratings",
        json={"movie_id": 1, "rating": 11},
    )
    assert resp.status_code == 422


async def test_add_rating_too_low(client):
    resp = await client.post(
        "/api/v1/users/1/ratings",
        json={"movie_id": 1, "rating": 0},
    )
    assert resp.status_code == 422


async def test_get_user_ratings_success(client, sample_rating):
    resp = await client.get("/api/v1/users/1/ratings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total"] == 1
    assert len(data["ratings"]) == 1
    assert data["ratings"][0]["rating"] == sample_rating.rating
    assert data["ratings"][0]["movie_title"] == "The Matrix"


async def test_get_user_ratings_pagination(client, mock_rating_service):
    resp = await client.get("/api/v1/users/1/ratings", params={"offset": 10, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["offset"] == 10
    assert data["limit"] == 5


async def test_get_user_ratings_empty(client, mock_rating_service):
    mock_rating_service.get_user_ratings.return_value = ([], 0)
    resp = await client.get("/api/v1/users/1/ratings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["ratings"] == []


# --- Bulk check endpoint tests ---


async def test_bulk_check_ratings_success(client, mock_rating_service):
    mock_rating_service.bulk_check.return_value = {1: 9, 3: 7}
    resp = await client.get(
        "/api/v1/users/1/ratings/check",
        params={"movie_ids": "1,2,3"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ratings"] == {"1": 9, "3": 7}


async def test_bulk_check_ratings_empty_result(client, mock_rating_service):
    mock_rating_service.bulk_check.return_value = {}
    resp = await client.get(
        "/api/v1/users/1/ratings/check",
        params={"movie_ids": "10,20"},
    )
    assert resp.status_code == 200
    assert resp.json()["ratings"] == {}


async def test_bulk_check_ratings_missing_param(client):
    resp = await client.get("/api/v1/users/1/ratings/check")
    assert resp.status_code == 422
