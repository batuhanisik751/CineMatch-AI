"""Tests for StreakService."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.streak_service import StreakService


@pytest.fixture()
def service():
    return StreakService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _make_streak_row(streak_start: date, streak_end: date, streak_len: int):
    row = MagicMock()
    row.streak_start = streak_start
    row.streak_end = streak_end
    row.streak_len = streak_len
    return row


def _setup_db(mock_db, total_ratings: int, streak_rows: list):
    """Configure mock_db.execute to return count then streak rows."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = total_ratings

    streak_result = MagicMock()
    streak_result.all.return_value = streak_rows

    mock_db.execute = AsyncMock(side_effect=[count_result, streak_result])


async def test_no_ratings(service, mock_db):
    _setup_db(mock_db, total_ratings=0, streak_rows=[])

    result = await service.get_streaks(1, mock_db)

    assert result["user_id"] == 1
    assert result["current_streak"] == 0
    assert result["longest_streak"] == 0
    assert result["total_ratings"] == 0
    assert len(result["milestones"]) == 7
    assert all(not m["reached"] for m in result["milestones"])


async def test_active_streak_today(service, mock_db):
    today = datetime.now(UTC).date()
    rows = [
        _make_streak_row(today - timedelta(days=4), today, 5),
    ]
    _setup_db(mock_db, total_ratings=30, streak_rows=rows)

    result = await service.get_streaks(1, mock_db)

    assert result["current_streak"] == 5
    assert result["longest_streak"] == 5


async def test_active_streak_yesterday(service, mock_db):
    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)
    rows = [
        _make_streak_row(yesterday - timedelta(days=2), yesterday, 3),
    ]
    _setup_db(mock_db, total_ratings=15, streak_rows=rows)

    result = await service.get_streaks(1, mock_db)

    assert result["current_streak"] == 3
    assert result["longest_streak"] == 3


async def test_expired_streak(service, mock_db):
    today = datetime.now(UTC).date()
    three_days_ago = today - timedelta(days=3)
    rows = [
        _make_streak_row(three_days_ago - timedelta(days=6), three_days_ago, 7),
    ]
    _setup_db(mock_db, total_ratings=20, streak_rows=rows)

    result = await service.get_streaks(1, mock_db)

    assert result["current_streak"] == 0
    assert result["longest_streak"] == 7


async def test_milestones_partial(service, mock_db):
    today = datetime.now(UTC).date()
    rows = [_make_streak_row(today, today, 1)]
    _setup_db(mock_db, total_ratings=55, streak_rows=rows)

    result = await service.get_streaks(1, mock_db)

    reached = [m for m in result["milestones"] if m["reached"]]
    unreached = [m for m in result["milestones"] if not m["reached"]]
    assert len(reached) == 3  # 10, 25, 50
    assert reached[0]["threshold"] == 10
    assert reached[1]["threshold"] == 25
    assert reached[2]["threshold"] == 50
    assert len(unreached) == 4  # 100, 250, 500, 1000


async def test_multiple_streaks_longest_not_most_recent(service, mock_db):
    today = datetime.now(UTC).date()
    # Most recent streak (2 days, ending today) — ordered first by streak_end DESC
    # Older but longer streak (10 days, ended 30 days ago)
    rows = [
        _make_streak_row(today - timedelta(days=1), today, 2),
        _make_streak_row(today - timedelta(days=40), today - timedelta(days=31), 10),
    ]
    _setup_db(mock_db, total_ratings=100, streak_rows=rows)

    result = await service.get_streaks(1, mock_db)

    assert result["current_streak"] == 2
    assert result["longest_streak"] == 10
