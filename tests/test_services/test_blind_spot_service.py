"""Tests for BlindSpotService."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.blind_spot_service import BlindSpotService


@pytest.fixture()
def service():
    return BlindSpotService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


_SENTINEL = object()


def _make_row(
    movie_id: int = 1,
    title: str = "Pulp Fiction",
    genres: list | None = _SENTINEL,
    vote_average: float = 8.9,
    vote_count: int = 20000,
    release_date: date | None = None,
    poster_path: str | None = "/pulp.jpg",
    original_language: str = "en",
    runtime: int = 154,
    popularity_score: float | None = None,
):
    row = MagicMock()
    row.id = movie_id
    row.title = title
    row.genres = ["Crime", "Drama"] if genres is _SENTINEL else genres
    row.vote_average = vote_average
    row.vote_count = vote_count
    row.release_date = release_date or date(1994, 10, 14)
    row.poster_path = poster_path
    row.original_language = original_language
    row.runtime = runtime
    if popularity_score is not None:
        row.popularity_score = popularity_score
    else:
        row.popularity_score = vote_count * vote_average
    return row


def _setup_db(mock_db, rows: list):
    result = MagicMock()
    result.all.return_value = rows
    mock_db.execute.return_value = result


@pytest.mark.asyncio
async def test_returns_popular_unrated_movies(service, mock_db):
    rows = [
        _make_row(movie_id=1, title="Pulp Fiction", vote_count=20000, vote_average=8.9),
        _make_row(movie_id=2, title="The Godfather", vote_count=18000, vote_average=9.2),
    ]
    _setup_db(mock_db, rows)

    result = await service.get_blind_spots(1, mock_db, limit=20)

    assert result["user_id"] == 1
    assert result["total"] == 2
    assert len(result["movies"]) == 2
    assert result["movies"][0]["movie"]["title"] == "Pulp Fiction"
    assert result["movies"][1]["movie"]["title"] == "The Godfather"
    assert result["genre"] is None


@pytest.mark.asyncio
async def test_empty_when_no_blind_spots(service, mock_db):
    _setup_db(mock_db, [])

    result = await service.get_blind_spots(1, mock_db)

    assert result["total"] == 0
    assert result["movies"] == []


@pytest.mark.asyncio
async def test_genre_filter_uses_jsonb_containment(service, mock_db):
    _setup_db(mock_db, [_make_row()])

    await service.get_blind_spots(1, mock_db, genre="Horror")

    call_args = mock_db.execute.call_args
    params = call_args[0][1]  # second positional arg is the params dict
    assert params["genre_filter"] == '["Horror"]'


@pytest.mark.asyncio
async def test_no_genre_by_default(service, mock_db):
    _setup_db(mock_db, [])

    await service.get_blind_spots(1, mock_db)

    call_args = mock_db.execute.call_args
    params = call_args[0][1]  # second positional arg is the params dict
    assert "genre_filter" not in params


@pytest.mark.asyncio
async def test_handles_none_genres(service, mock_db):
    _setup_db(mock_db, [_make_row(genres=None)])

    result = await service.get_blind_spots(1, mock_db)

    assert result["movies"][0]["movie"]["genres"] == []


@pytest.mark.asyncio
async def test_passes_limit(service, mock_db):
    _setup_db(mock_db, [])

    await service.get_blind_spots(1, mock_db, limit=5)

    call_args = mock_db.execute.call_args
    params = call_args[0][1]  # second positional arg is the params dict
    assert params["lim"] == 5


@pytest.mark.asyncio
async def test_popularity_score_in_output(service, mock_db):
    _setup_db(mock_db, [_make_row(vote_count=20000, vote_average=8.9)])

    result = await service.get_blind_spots(1, mock_db)

    score = result["movies"][0]["popularity_score"]
    assert isinstance(score, float)
    assert score == 20000 * 8.9


@pytest.mark.asyncio
async def test_movie_summary_fields_populated(service, mock_db):
    _setup_db(mock_db, [_make_row()])

    result = await service.get_blind_spots(1, mock_db)

    movie = result["movies"][0]["movie"]
    assert movie["id"] == 1
    assert movie["title"] == "Pulp Fiction"
    assert movie["genres"] == ["Crime", "Drama"]
    assert movie["vote_average"] == 8.9
    assert movie["release_date"] == date(1994, 10, 14)
    assert movie["poster_path"] == "/pulp.jpg"
    assert movie["original_language"] == "en"
    assert movie["runtime"] == 154


@pytest.mark.asyncio
async def test_genre_returned_in_response(service, mock_db):
    _setup_db(mock_db, [])

    result = await service.get_blind_spots(1, mock_db, genre="Horror")

    assert result["genre"] == "Horror"
