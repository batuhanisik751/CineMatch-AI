"""Tests for UserListService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.user_list_service import UserListService


@pytest.fixture()
def service():
    return UserListService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _mock_user_list(id=1, user_id=1, name="Favorites"):
    ul = MagicMock()
    ul.id = id
    ul.user_id = user_id
    ul.name = name
    ul.description = "My favorite movies"
    ul.is_public = False
    ul.created_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    ul.updated_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    return ul


def _mock_list_item(list_id=1, movie_id=1, position=0):
    item = MagicMock()
    item.id = 1
    item.list_id = list_id
    item.movie_id = movie_id
    item.position = position
    item.added_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    item.movie_title = None
    item.poster_path = None
    item.genres = []
    item.vote_average = 0.0
    item.release_date = None
    return item


@pytest.mark.asyncio
async def test_create_list(service, mock_db):
    """Create a new list for an existing user."""
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = MagicMock()

    mock_db.execute = AsyncMock(return_value=user_result)
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()

    await service.create_list(1, "Favorites", "My faves", False, mock_db)

    assert mock_db.commit.await_count == 1
    assert mock_db.add.call_count == 1


@pytest.mark.asyncio
async def test_create_list_creates_user_if_missing(service, mock_db):
    """Auto-create user if not found."""
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(return_value=user_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    await service.create_list(999, "Test", None, False, mock_db)

    # user add + list add = 2 calls
    assert mock_db.add.call_count == 2
    assert mock_db.flush.await_count == 1


@pytest.mark.asyncio
async def test_update_list_success(service, mock_db):
    """Update a list owned by the user."""
    ul = _mock_user_list()
    result = MagicMock()
    result.scalar_one_or_none.return_value = ul

    mock_db.execute = AsyncMock(return_value=result)
    mock_db.refresh = AsyncMock()

    updated = await service.update_list(1, 1, mock_db, name="New Name")

    assert updated is not None
    assert updated.name == "New Name"
    assert mock_db.commit.await_count == 1


@pytest.mark.asyncio
async def test_update_list_not_owned(service, mock_db):
    """Return None if list not owned by user."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(return_value=result)

    updated = await service.update_list(2, 1, mock_db, name="Hacked")

    assert updated is None


@pytest.mark.asyncio
async def test_delete_list_success(service, mock_db):
    """Delete a list owned by user."""
    delete_result = MagicMock()
    delete_result.rowcount = 1

    mock_db.execute = AsyncMock(return_value=delete_result)

    deleted = await service.delete_list(1, 1, mock_db)

    assert deleted is True
    assert mock_db.commit.await_count == 1


@pytest.mark.asyncio
async def test_delete_list_not_found(service, mock_db):
    """Return False if list doesn't exist or not owned."""
    delete_result = MagicMock()
    delete_result.rowcount = 0

    mock_db.execute = AsyncMock(return_value=delete_result)

    deleted = await service.delete_list(2, 99, mock_db)

    assert deleted is False


@pytest.mark.asyncio
async def test_add_item_returns_none_for_unowned_list(service, mock_db):
    """Return None when trying to add to a list not owned by user."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(return_value=result)

    item = await service.add_item(2, 1, 100, mock_db)

    assert item is None


@pytest.mark.asyncio
async def test_remove_item_returns_false_for_unowned_list(service, mock_db):
    """Return False when list not owned by user."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(return_value=result)

    removed = await service.remove_item(2, 1, 100, mock_db)

    assert removed is False


@pytest.mark.asyncio
async def test_reorder_items_returns_false_for_unowned_list(service, mock_db):
    """Return False when list not owned by user."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(return_value=result)

    success = await service.reorder_items(2, 1, [1, 2, 3], mock_db)

    assert success is False
