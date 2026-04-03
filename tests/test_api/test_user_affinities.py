"""Tests for the affinities API endpoint."""

from __future__ import annotations


async def test_get_affinities_success(client, mock_user_stats_service):
    mock_user_stats_service.get_affinities.return_value = {
        "user_id": 1,
        "directors": [
            {
                "name": "Nolan",
                "role": "director",
                "avg_rating": 8.5,
                "count": 3,
                "weighted_score": 11.78,
                "films_rated": [
                    {"movie_id": 1, "title": "Inception", "rating": 9, "poster_path": "/inc.jpg"},
                ],
            }
        ],
        "actors": [
            {
                "name": "DiCaprio",
                "role": "actor",
                "avg_rating": 7.5,
                "count": 2,
                "weighted_score": 8.24,
                "films_rated": [
                    {"movie_id": 1, "title": "Inception", "rating": 9, "poster_path": "/inc.jpg"},
                ],
            }
        ],
    }

    resp = await client.get("/api/v1/users/1/affinities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert len(data["directors"]) == 1
    assert data["directors"][0]["name"] == "Nolan"
    assert data["directors"][0]["weighted_score"] == 11.78
    assert len(data["directors"][0]["films_rated"]) == 1
    assert len(data["actors"]) == 1
    assert data["actors"][0]["name"] == "DiCaprio"
    mock_user_stats_service.get_affinities.assert_called_once()


async def test_get_affinities_empty(client, mock_user_stats_service):
    mock_user_stats_service.get_affinities.return_value = {
        "user_id": 1,
        "directors": [],
        "actors": [],
    }

    resp = await client.get("/api/v1/users/1/affinities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["directors"] == []
    assert data["actors"] == []


async def test_get_affinities_custom_limit(client, mock_user_stats_service):
    mock_user_stats_service.get_affinities.return_value = {
        "user_id": 1,
        "directors": [],
        "actors": [],
    }

    resp = await client.get("/api/v1/users/1/affinities?limit=5")
    assert resp.status_code == 200
    mock_user_stats_service.get_affinities.assert_called_once()
