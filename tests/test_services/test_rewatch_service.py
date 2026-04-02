"""Tests for RewatchService."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.rewatch_service import RewatchService


@pytest.fixture()
def service():
    return RewatchService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


_SENTINEL = object()


def _make_row(
    movie_id: int = 1,
    title: str = "The Matrix",
    genres: list | None = _SENTINEL,
    vote_average: float = 8.7,
    vote_count: int = 5000,
    release_date: date | None = None,
    poster_path: str | None = "/matrix.jpg",
    original_language: str = "en",
    runtime: int = 136,
    user_rating: int = 9,
    rated_at: datetime | None = None,
    days_since_rated: int = 900,
    is_classic: bool = True,
):
    row = MagicMock()
    row.id = movie_id
    row.title = title
    row.genres = ["Action", "Sci-Fi"] if genres is _SENTINEL else genres
    row.vote_average = vote_average
    row.vote_count = vote_count
    row.release_date = release_date or date(1999, 3, 31)
    row.poster_path = poster_path
    row.original_language = original_language
    row.runtime = runtime
    row.user_rating = user_rating
    row.rated_at = rated_at or datetime(2022, 1, 15, tzinfo=UTC)
    row.days_since_rated = days_since_rated
    row.is_classic = is_classic
    return row


def _setup_db(mock_db, rows: list):
    result = MagicMock()
    result.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result)


async def test_returns_old_high_rated_movies(service, mock_db):
    rows = [
        _make_row(movie_id=1, title="The Matrix", user_rating=9, days_since_rated=1200),
        _make_row(movie_id=2, title="Inception", user_rating=8, days_since_rated=900),
    ]
    _setup_db(mock_db, rows)

    result = await service.get_rewatch_suggestions(1, mock_db)

    assert result["user_id"] == 1
    assert result["total"] == 2
    assert len(result["suggestions"]) == 2
    assert result["suggestions"][0]["movie"]["title"] == "The Matrix"
    assert result["suggestions"][0]["user_rating"] == 9
    assert result["suggestions"][0]["days_since_rated"] == 1200
    assert result["suggestions"][1]["movie"]["title"] == "Inception"


async def test_empty_result_for_no_qualifying_ratings(service, mock_db):
    _setup_db(mock_db, [])

    result = await service.get_rewatch_suggestions(1, mock_db)

    assert result["user_id"] == 1
    assert result["total"] == 0
    assert result["suggestions"] == []


async def test_classic_flag_set_correctly(service, mock_db):
    rows = [
        _make_row(movie_id=1, is_classic=True, vote_count=5000, vote_average=8.5),
        _make_row(movie_id=2, is_classic=False, vote_count=50, vote_average=6.0),
    ]
    _setup_db(mock_db, rows)

    result = await service.get_rewatch_suggestions(1, mock_db)

    assert result["suggestions"][0]["is_classic"] is True
    assert result["suggestions"][1]["is_classic"] is False


async def test_movie_summary_fields_populated(service, mock_db):
    rows = [
        _make_row(
            movie_id=42,
            title="Blade Runner",
            genres=["Sci-Fi", "Drama"],
            vote_average=8.1,
            release_date=date(1982, 6, 25),
            poster_path="/blade.jpg",
            original_language="en",
            runtime=117,
        ),
    ]
    _setup_db(mock_db, rows)

    result = await service.get_rewatch_suggestions(1, mock_db)
    movie = result["suggestions"][0]["movie"]

    assert movie["id"] == 42
    assert movie["title"] == "Blade Runner"
    assert movie["genres"] == ["Sci-Fi", "Drama"]
    assert movie["vote_average"] == 8.1
    assert movie["poster_path"] == "/blade.jpg"
    assert movie["runtime"] == 117


async def test_passes_parameters_to_query(service, mock_db):
    _setup_db(mock_db, [])

    await service.get_rewatch_suggestions(
        42,
        mock_db,
        limit=5,
        min_rating=9,
    )

    call_args = mock_db.execute.call_args
    params = call_args[0][1]
    assert params["uid"] == 42
    assert params["min_rating"] == 9
    assert params["lim"] == 5


async def test_handles_none_genres(service, mock_db):
    rows = [_make_row(genres=None)]
    _setup_db(mock_db, rows)

    result = await service.get_rewatch_suggestions(1, mock_db)

    assert result["suggestions"][0]["movie"]["genres"] == []
