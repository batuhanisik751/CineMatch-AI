"""Tests for GlobalStatsService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.global_stats_service import GlobalStatsService


@pytest.fixture()
def service():
    return GlobalStatsService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _setup_db(
    mock_db,
    *,
    total_movies: int = 1000,
    total_users: int = 500,
    total_ratings: int = 50000,
    avg_rating: float = 6.8,
    most_rated_row=None,
    highest_rated_row=None,
    most_active_row=None,
    ratings_this_week: int = 120,
):
    """Configure mock_db.execute to return results for all 7 queries in order."""

    # A: total movies
    movies_result = MagicMock()
    movies_result.scalar_one.return_value = total_movies

    # B: total users
    users_result = MagicMock()
    users_result.scalar_one.return_value = total_users

    # C: total ratings + avg
    rating_agg = MagicMock()
    rating_agg.total = total_ratings
    rating_agg.avg = avg_rating
    rating_agg_result = MagicMock()
    rating_agg_result.one.return_value = rating_agg

    # D: most rated movie
    most_rated_result = MagicMock()
    most_rated_result.first.return_value = most_rated_row

    # E: highest rated movie
    highest_rated_result = MagicMock()
    highest_rated_result.first.return_value = highest_rated_row

    # F: most active user
    most_active_result = MagicMock()
    most_active_result.first.return_value = most_active_row

    # G: ratings this week
    week_result = MagicMock()
    week_result.scalar_one.return_value = ratings_this_week

    mock_db.execute = AsyncMock(
        side_effect=[
            movies_result,
            users_result,
            rating_agg_result,
            most_rated_result,
            highest_rated_result,
            most_active_result,
            week_result,
        ]
    )


def _make_movie_row(
    *,
    id: int = 1,
    title: str = "The Shawshank Redemption",
    poster_path: str = "/poster.jpg",
    vote_average: float = 8.7,
    genres: list[str] | None = None,
    release_date: str = "1994-09-23",
    rating_count: int = 5000,
    avg_user_rating: float | None = None,
):
    row = MagicMock()
    row.id = id
    row.title = title
    row.poster_path = poster_path
    row.vote_average = vote_average
    row.genres = genres or ["Drama"]
    row.release_date = release_date
    row.rating_count = rating_count
    if avg_user_rating is not None:
        row.avg_user_rating = avg_user_rating
    return row


def _make_user_row(*, id: int = 42, movielens_id: int = 42, rating_count: int = 3000):
    row = MagicMock()
    row.id = id
    row.movielens_id = movielens_id
    row.rating_count = rating_count
    return row


async def test_get_global_stats_with_data(service, mock_db):
    most_rated = _make_movie_row(rating_count=5000)
    highest_rated = _make_movie_row(
        id=2,
        title="The Godfather",
        rating_count=3000,
        avg_user_rating=9.1,
    )
    most_active = _make_user_row()

    _setup_db(
        mock_db,
        most_rated_row=most_rated,
        highest_rated_row=highest_rated,
        most_active_row=most_active,
    )

    result = await service.get_global_stats(mock_db)

    assert result["total_movies"] == 1000
    assert result["total_users"] == 500
    assert result["total_ratings"] == 50000
    assert result["avg_rating"] == 6.8
    assert result["ratings_this_week"] == 120

    assert result["most_rated_movie"] is not None
    assert result["most_rated_movie"]["title"] == "The Shawshank Redemption"
    assert result["most_rated_movie"]["rating_count"] == 5000

    assert result["highest_rated_movie"] is not None
    assert result["highest_rated_movie"]["title"] == "The Godfather"
    assert result["highest_rated_movie"]["avg_user_rating"] == 9.1

    assert result["most_active_user"] is not None
    assert result["most_active_user"]["id"] == 42
    assert result["most_active_user"]["rating_count"] == 3000


async def test_get_global_stats_empty_database(service, mock_db):
    _setup_db(
        mock_db,
        total_movies=0,
        total_users=0,
        total_ratings=0,
        avg_rating=0,
        ratings_this_week=0,
    )

    result = await service.get_global_stats(mock_db)

    assert result["total_movies"] == 0
    assert result["total_users"] == 0
    assert result["total_ratings"] == 0
    assert result["avg_rating"] == 0.0
    assert result["most_rated_movie"] is None
    assert result["highest_rated_movie"] is None
    assert result["most_active_user"] is None
    assert result["ratings_this_week"] == 0


async def test_get_global_stats_no_qualified_highest_rated(service, mock_db):
    """When no movie has enough ratings, highest_rated_movie should be None."""
    most_rated = _make_movie_row(rating_count=30)

    _setup_db(
        mock_db,
        most_rated_row=most_rated,
        highest_rated_row=None,  # no movie qualifies
        most_active_row=_make_user_row(),
    )

    result = await service.get_global_stats(mock_db)

    assert result["most_rated_movie"] is not None
    assert result["highest_rated_movie"] is None
