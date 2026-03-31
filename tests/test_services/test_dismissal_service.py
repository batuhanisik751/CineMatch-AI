"""Tests for DismissalService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.dismissal_service import DismissalService


@pytest.fixture()
def service():
    return DismissalService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _mock_dismissal(user_id=1, movie_id=1):
    item = MagicMock()
    item.id = 1
    item.user_id = user_id
    item.movie_id = movie_id
    item.dismissed_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    item.movie_title = None
    return item


@pytest.mark.asyncio
async def test_dismiss_movie_new_entry(service, mock_db):
    """Dismiss a movie when user exists."""
    dismissal = _mock_dismissal()

    # First execute: user exists check
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = MagicMock()

    # Second execute: insert on conflict do nothing
    insert_result = MagicMock()

    # Third execute: select the row
    select_result = MagicMock()
    select_result.scalar_one.return_value = dismissal

    mock_db.execute = AsyncMock(side_effect=[user_result, insert_result, select_result])

    result = await service.dismiss_movie(1, 1, mock_db)

    assert result.user_id == 1
    assert result.movie_id == 1
    assert mock_db.commit.await_count == 1


@pytest.mark.asyncio
async def test_dismiss_movie_idempotent(service, mock_db):
    """Dismissing an already-dismissed movie returns the existing entry."""
    dismissal = _mock_dismissal()

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = MagicMock()

    insert_result = MagicMock()

    select_result = MagicMock()
    select_result.scalar_one.return_value = dismissal

    mock_db.execute = AsyncMock(side_effect=[user_result, insert_result, select_result])

    result = await service.dismiss_movie(1, 1, mock_db)

    assert result.user_id == 1
    assert result.movie_id == 1


@pytest.mark.asyncio
async def test_undismiss_movie_exists(service, mock_db):
    """Undismissing an existing dismissal returns True."""
    delete_result = MagicMock()
    delete_result.rowcount = 1
    mock_db.execute = AsyncMock(return_value=delete_result)

    result = await service.undismiss_movie(1, 1, mock_db)

    assert result is True
    assert mock_db.commit.await_count == 1


@pytest.mark.asyncio
async def test_undismiss_movie_not_found(service, mock_db):
    """Undismissing a non-existent dismissal returns False."""
    delete_result = MagicMock()
    delete_result.rowcount = 0
    mock_db.execute = AsyncMock(return_value=delete_result)

    result = await service.undismiss_movie(1, 999, mock_db)

    assert result is False


@pytest.mark.asyncio
async def test_get_dismissed_movie_ids(service, mock_db):
    """Get all dismissed movie IDs for a user."""
    result = MagicMock()
    result.all.return_value = [(1,), (5,), (10,)]
    mock_db.execute = AsyncMock(return_value=result)

    dismissed = await service.get_dismissed_movie_ids(1, mock_db)

    assert dismissed == {1, 5, 10}


@pytest.mark.asyncio
async def test_get_dismissed_movie_ids_empty(service, mock_db):
    """User with no dismissals returns empty set."""
    result = MagicMock()
    result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=result)

    dismissed = await service.get_dismissed_movie_ids(1, mock_db)

    assert dismissed == set()


@pytest.mark.asyncio
async def test_get_dismissals_paginated(service, mock_db):
    """Get paginated dismissals with movie details."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 3

    row1 = (_mock_dismissal(movie_id=10), "Movie A", "/a.jpg", ["Action"], 7.5, "2020-01-01")
    row2 = (_mock_dismissal(movie_id=5), "Movie B", "/b.jpg", ["Drama"], 8.0, "2019-06-15")
    row3 = (_mock_dismissal(movie_id=1), "Movie C", None, None, 6.0, None)
    rows_result = MagicMock()
    rows_result.all.return_value = [row1, row2, row3]

    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    rows, total = await service.get_dismissals(1, mock_db, offset=0, limit=100)

    assert total == 3
    assert len(rows) == 3
    assert rows[0][1] == "Movie A"


@pytest.mark.asyncio
async def test_bulk_check_partial_match(service, mock_db):
    """Bulk check returns only the IDs that are dismissed."""
    result = MagicMock()
    result.all.return_value = [(1,), (3,)]
    mock_db.execute = AsyncMock(return_value=result)

    matched = await service.bulk_check(1, [1, 2, 3, 4], mock_db)

    assert matched == {1, 3}


@pytest.mark.asyncio
async def test_bulk_check_empty_input(service, mock_db):
    """Bulk check with empty list returns empty set without querying."""
    result = await service.bulk_check(1, [], mock_db)

    assert result == set()
    mock_db.execute.assert_not_awaited()
