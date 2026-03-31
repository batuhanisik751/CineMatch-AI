"""Tests for UserStatsService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.user_stats_service import UserStatsService


@pytest.fixture()
def service():
    return UserStatsService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _row(*values):
    """Create a mock row accessible by index and attribute."""
    r = MagicMock()
    for i, v in enumerate(values):
        r.__getitem__ = lambda self, idx, vals=values: vals[idx]
    return r


async def test_get_user_stats_with_ratings(service, mock_db):
    """Full stats with data for all 6 queries."""
    # A: total + average
    totals_row = MagicMock()
    totals_row.total = 5
    totals_row.average = 3.8
    totals_result = MagicMock()
    totals_result.one.return_value = totals_row

    # B: genre distribution
    genre_result = MagicMock()
    genre_result.all.return_value = [("Action", 3), ("Comedy", 2)]

    # C: rating distribution
    rating_row_1 = MagicMock(rating=8, cnt=3)
    rating_row_2 = MagicMock(rating=10, cnt=2)
    rating_result = MagicMock()
    rating_result.all.return_value = [rating_row_1, rating_row_2]

    # D: top directors
    director_row = MagicMock(director="Nolan", cnt=3)
    director_result = MagicMock()
    director_result.all.return_value = [director_row]

    # E: top actors
    actor_result = MagicMock()
    actor_result.all.return_value = [("DiCaprio", 2)]

    # F: timeline
    timeline_result = MagicMock()
    timeline_result.all.return_value = [("2024-01", 3), ("2024-02", 2)]

    mock_db.execute = AsyncMock(
        side_effect=[
            totals_result,
            genre_result,
            rating_result,
            director_result,
            actor_result,
            timeline_result,
        ]
    )

    stats = await service.get_user_stats(1, mock_db)

    assert stats["user_id"] == 1
    assert stats["total_ratings"] == 5
    assert stats["average_rating"] == 3.8
    assert len(stats["genre_distribution"]) == 2
    assert stats["genre_distribution"][0]["genre"] == "Action"
    assert stats["genre_distribution"][0]["percentage"] == 60.0
    assert stats["genre_distribution"][1]["percentage"] == 40.0
    assert len(stats["rating_distribution"]) == 10  # all buckets
    assert stats["top_directors"][0]["name"] == "Nolan"
    assert stats["top_actors"][0]["name"] == "DiCaprio"
    assert len(stats["rating_timeline"]) == 2


async def test_get_user_stats_no_ratings(service, mock_db):
    """User with zero ratings returns empty stats."""
    totals_row = MagicMock()
    totals_row.total = 0
    totals_row.average = 0
    totals_result = MagicMock()
    totals_result.one.return_value = totals_row

    mock_db.execute = AsyncMock(return_value=totals_result)

    stats = await service.get_user_stats(1, mock_db)

    assert stats["total_ratings"] == 0
    assert stats["average_rating"] == 0.0
    assert stats["genre_distribution"] == []
    assert stats["top_directors"] == []
    assert stats["top_actors"] == []
    assert stats["rating_timeline"] == []
    # Rating distribution still has all 10 buckets with 0 counts
    assert len(stats["rating_distribution"]) == 10
    assert all(b["count"] == 0 for b in stats["rating_distribution"])


async def test_rating_distribution_fills_missing_buckets(service, mock_db):
    """Only some rating values present — all 10 buckets should still appear."""
    totals_row = MagicMock()
    totals_row.total = 2
    totals_row.average = 9
    totals_result = MagicMock()
    totals_result.one.return_value = totals_row

    genre_result = MagicMock()
    genre_result.all.return_value = [("Drama", 2)]

    rating_row = MagicMock(rating=9, cnt=2)
    rating_result = MagicMock()
    rating_result.all.return_value = [rating_row]

    director_result = MagicMock()
    director_result.all.return_value = []

    actor_result = MagicMock()
    actor_result.all.return_value = []

    timeline_result = MagicMock()
    timeline_result.all.return_value = [("2024-03", 2)]

    mock_db.execute = AsyncMock(
        side_effect=[
            totals_result,
            genre_result,
            rating_result,
            director_result,
            actor_result,
            timeline_result,
        ]
    )

    stats = await service.get_user_stats(1, mock_db)

    assert len(stats["rating_distribution"]) == 10
    bucket_map = {b["rating"]: b["count"] for b in stats["rating_distribution"]}
    assert bucket_map["9"] == 2
    assert bucket_map["1"] == 0
    assert bucket_map["10"] == 0


async def test_genre_percentages_calculated_correctly(service, mock_db):
    """Genre percentages should sum to 100%."""
    totals_row = MagicMock()
    totals_row.total = 10
    totals_row.average = 3.5
    totals_result = MagicMock()
    totals_result.one.return_value = totals_row

    genre_result = MagicMock()
    genre_result.all.return_value = [("Action", 5), ("Comedy", 3), ("Drama", 2)]

    rating_result = MagicMock()
    rating_result.all.return_value = []

    director_result = MagicMock()
    director_result.all.return_value = []

    actor_result = MagicMock()
    actor_result.all.return_value = []

    timeline_result = MagicMock()
    timeline_result.all.return_value = []

    mock_db.execute = AsyncMock(
        side_effect=[
            totals_result,
            genre_result,
            rating_result,
            director_result,
            actor_result,
            timeline_result,
        ]
    )

    stats = await service.get_user_stats(1, mock_db)

    total_pct = sum(g["percentage"] for g in stats["genre_distribution"])
    assert abs(total_pct - 100.0) < 0.1
    assert stats["genre_distribution"][0]["percentage"] == 50.0
    assert stats["genre_distribution"][1]["percentage"] == 30.0
    assert stats["genre_distribution"][2]["percentage"] == 20.0


# --- Diary (get_diary) tests ---


async def test_get_diary_returns_grouped_days(service, mock_db):
    """Diary groups rows by date and computes total_ratings."""
    from datetime import date

    diary_result = MagicMock()
    diary_result.all.return_value = [
        (date(2025, 3, 1), 10, "Inception", 9),
        (date(2025, 3, 1), 20, "Interstellar", 8),
        (date(2025, 3, 5), 30, "Tenet", 7),
    ]
    mock_db.execute = AsyncMock(return_value=diary_result)

    result = await service.get_diary(1, 2025, mock_db)

    assert result["user_id"] == 1
    assert result["year"] == 2025
    assert result["total_ratings"] == 3
    assert len(result["days"]) == 2

    day1 = result["days"][0]
    assert day1["date"] == "2025-03-01"
    assert day1["count"] == 2
    assert day1["movies"][0]["id"] == 10
    assert day1["movies"][1]["title"] == "Interstellar"

    day2 = result["days"][1]
    assert day2["date"] == "2025-03-05"
    assert day2["count"] == 1
    assert day2["movies"][0]["rating"] == 7


async def test_get_diary_empty_year(service, mock_db):
    """Diary for a year with no ratings returns empty days list."""
    diary_result = MagicMock()
    diary_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=diary_result)

    result = await service.get_diary(1, 2020, mock_db)

    assert result["user_id"] == 1
    assert result["year"] == 2020
    assert result["days"] == []
    assert result["total_ratings"] == 0
