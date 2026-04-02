"""Tests for import/export ratings API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture()
def mock_resolve_imdb():
    with patch("cinematch.api.v1.ratings.resolve_movies_imdb", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture()
def mock_resolve_letterboxd():
    with patch(
        "cinematch.api.v1.ratings.resolve_movies_letterboxd", new_callable=AsyncMock
    ) as mock:
        yield mock


def _imdb_csv() -> bytes:
    return (
        b"Const,Your Rating,Date Rated,Title,URL,Title Type,"  # noqa: E501
        b"IMDb Rating,Runtime (mins),Year,Genres,Num Votes,Release Date,Directors\n"
        b"tt0133093,9,2024-01-01,The Matrix,,Movie,"
        b"8.7,136,1999,Action,2000000,1999-03-31,Lana Wachowski\n"
        b"tt0468569,10,2024-01-01,The Dark Knight,,Movie,"
        b"9.0,152,2008,Action,2500000,2008-07-18,Christopher Nolan\n"
    )


def _letterboxd_csv() -> bytes:
    return (
        b"Date,Name,Year,Letterboxd URI,Rating\n"
        b"2024-01-01,Inception,2010,https://letterboxd.com/film/inception/,4.5\n"
        b"2024-01-02,Interstellar,2014,https://letterboxd.com/film/interstellar/,4.0\n"
    )


async def test_import_imdb_csv(client, mock_rating_service, mock_resolve_imdb):
    mock_rating_service.bulk_check.return_value = {}
    mock_rating_service.import_ratings.return_value = {"imported": 2, "updated": 0}
    mock_resolve_imdb.return_value = [
        {
            "imdb_id": "tt0133093",
            "title": "The Matrix",
            "year": 1999,
            "original_rating": 9,
            "scaled_rating": 9,
            "movie_id": 1,
            "status": "pending",
        },
        {
            "imdb_id": "tt0468569",
            "title": "The Dark Knight",
            "year": 2008,
            "original_rating": 10,
            "scaled_rating": 10,
            "movie_id": 2,
            "status": "pending",
        },
    ]

    resp = await client.post(
        "/api/v1/users/1/ratings/import?source=imdb",
        files={"file": ("ratings.csv", _imdb_csv(), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "imdb"
    assert data["imported"] == 2
    assert data["updated"] == 0
    assert data["not_found"] == 0
    assert data["total_rows"] == 2
    assert len(data["results"]) == 2


async def test_import_letterboxd_csv(client, mock_rating_service, mock_resolve_letterboxd):
    mock_rating_service.bulk_check.return_value = {}
    mock_rating_service.import_ratings.return_value = {"imported": 2, "updated": 0}
    mock_resolve_letterboxd.return_value = [
        {
            "title": "Inception",
            "year": 2010,
            "original_rating": 4.5,
            "scaled_rating": 9,
            "movie_id": 10,
            "status": "pending",
        },
        {
            "title": "Interstellar",
            "year": 2014,
            "original_rating": 4.0,
            "scaled_rating": 8,
            "movie_id": 20,
            "status": "pending",
        },
    ]

    resp = await client.post(
        "/api/v1/users/1/ratings/import?source=letterboxd",
        files={"file": ("ratings.csv", _letterboxd_csv(), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "letterboxd"
    assert data["imported"] == 2
    assert data["not_found"] == 0


async def test_import_with_not_found(client, mock_rating_service, mock_resolve_imdb):
    mock_rating_service.bulk_check.return_value = {}
    mock_rating_service.import_ratings.return_value = {"imported": 1, "updated": 0}
    mock_resolve_imdb.return_value = [
        {
            "imdb_id": "tt0133093",
            "title": "The Matrix",
            "year": 1999,
            "original_rating": 9,
            "scaled_rating": 9,
            "movie_id": 1,
            "status": "pending",
        },
        {
            "imdb_id": "tt0468569",
            "title": "The Dark Knight",
            "year": 2008,
            "original_rating": 10,
            "scaled_rating": 10,
            "movie_id": None,
            "status": "not_found",
        },
    ]

    resp = await client.post(
        "/api/v1/users/1/ratings/import?source=imdb",
        files={"file": ("ratings.csv", _imdb_csv(), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1
    assert data["not_found"] == 1
    not_found = [r for r in data["results"] if r["status"] == "not_found"]
    assert len(not_found) == 1
    assert not_found[0]["title"] == "The Dark Knight"


async def test_import_empty_csv(client):
    resp = await client.post(
        "/api/v1/users/1/ratings/import",
        files={"file": ("ratings.csv", b"", "text/csv")},
    )
    assert resp.status_code == 422


async def test_import_unrecognized_format(client):
    csv_content = b"col1,col2,col3\nval1,val2,val3\n"
    resp = await client.post(
        "/api/v1/users/1/ratings/import?source=auto",
        files={"file": ("data.csv", csv_content, "text/csv")},
    )
    assert resp.status_code == 422
    assert "Unrecognized" in resp.json()["detail"]


async def test_export_ratings_csv(client, mock_rating_service):
    mock_rating_service.export_ratings.return_value = [
        (1, "The Matrix", "tt0133093", 603, 9, datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)),
    ]

    resp = await client.get("/api/v1/users/1/ratings/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "cinematch_ratings_1.csv" in resp.headers.get("content-disposition", "")

    lines = resp.text.strip().splitlines()
    assert len(lines) == 2  # header + 1 data row
    assert lines[0].strip() == "movie_id,title,imdb_id,tmdb_id,rating,timestamp"
    assert "The Matrix" in lines[1]
    assert "tt0133093" in lines[1]


async def test_export_ratings_empty(client, mock_rating_service):
    mock_rating_service.export_ratings.return_value = []

    resp = await client.get("/api/v1/users/1/ratings/export")
    assert resp.status_code == 200
    lines = resp.text.strip().splitlines()
    assert len(lines) == 1  # header only
    assert lines[0] == "movie_id,title,imdb_id,tmdb_id,rating,timestamp"
