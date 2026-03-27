"""Tests for WatchlistService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.watchlist_service import WatchlistService


@pytest.fixture()
def service():
    return WatchlistService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _mock_watchlist_item(user_id=1, movie_id=1):
    item = MagicMock()
    item.id = 1
    item.user_id = user_id
    item.movie_id = movie_id
    item.added_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    return item


@pytest.mark.asyncio
async def test_add_to_watchlist_new_entry(service, mock_db):
    """Add a movie to watchlist when user exists."""
    item = _mock_watchlist_item()

    # First execute: user exists check
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = MagicMock()  # user exists

    # Second execute: insert on conflict do nothing
    insert_result = MagicMock()

    # Third execute: select the row
    select_result = MagicMock()
    select_result.scalar_one.return_value = item

    mock_db.execute = AsyncMock(side_effect=[user_result, insert_result, select_result])

    result = await service.add_to_watchlist(1, 1, mock_db)

    assert result.user_id == 1
    assert result.movie_id == 1
    assert mock_db.commit.await_count == 1


@pytest.mark.asyncio
async def test_add_to_watchlist_already_exists(service, mock_db):
    """Adding a movie that's already in the watchlist returns the existing item."""
    item = _mock_watchlist_item()

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = MagicMock()

    insert_result = MagicMock()

    select_result = MagicMock()
    select_result.scalar_one.return_value = item

    mock_db.execute = AsyncMock(side_effect=[user_result, insert_result, select_result])

    result = await service.add_to_watchlist(1, 1, mock_db)

    assert result.user_id == 1
    assert result.movie_id == 1


@pytest.mark.asyncio
async def test_remove_from_watchlist_exists(service, mock_db):
    """Removing an existing watchlist item returns True."""
    delete_result = MagicMock()
    delete_result.rowcount = 1
    mock_db.execute = AsyncMock(return_value=delete_result)

    result = await service.remove_from_watchlist(1, 1, mock_db)

    assert result is True
    assert mock_db.commit.await_count == 1


@pytest.mark.asyncio
async def test_remove_from_watchlist_not_found(service, mock_db):
    """Removing a non-existent watchlist item returns False."""
    delete_result = MagicMock()
    delete_result.rowcount = 0
    mock_db.execute = AsyncMock(return_value=delete_result)

    result = await service.remove_from_watchlist(1, 999, mock_db)

    assert result is False


@pytest.mark.asyncio
async def test_get_watchlist_paginated(service, mock_db):
    """Get paginated watchlist with movie details."""
    item = _mock_watchlist_item()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    rows_result = MagicMock()
    rows_result.all.return_value = [
        (item, "The Matrix", "/poster.jpg", ["Action"], 8.2, "1999-03-31"),
    ]

    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    rows, total = await service.get_watchlist(1, mock_db, offset=0, limit=20)

    assert total == 1
    assert len(rows) == 1
    assert rows[0][1] == "The Matrix"


@pytest.mark.asyncio
async def test_get_watchlist_empty(service, mock_db):
    """Empty watchlist returns empty list and total 0."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    rows_result = MagicMock()
    rows_result.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[count_result, rows_result])

    rows, total = await service.get_watchlist(1, mock_db)

    assert total == 0
    assert rows == []


@pytest.mark.asyncio
async def test_is_in_watchlist_true(service, mock_db):
    """Movie in watchlist returns True."""
    result = MagicMock()
    result.scalar_one.return_value = 1
    mock_db.execute = AsyncMock(return_value=result)

    assert await service.is_in_watchlist(1, 1, mock_db) is True


@pytest.mark.asyncio
async def test_is_in_watchlist_false(service, mock_db):
    """Movie not in watchlist returns False."""
    result = MagicMock()
    result.scalar_one.return_value = 0
    mock_db.execute = AsyncMock(return_value=result)

    assert await service.is_in_watchlist(1, 999, mock_db) is False


@pytest.mark.asyncio
async def test_bulk_check_partial_match(service, mock_db):
    """Bulk check returns only the IDs that are in the watchlist."""
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
