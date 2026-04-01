"""Tests for OnboardingService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.onboarding_service import OnboardingService


@pytest.fixture()
def service():
    return OnboardingService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_onboarding_status_incomplete(service, mock_db):
    """Status is incomplete when rating count < threshold."""
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = 3
    mock_db.execute = AsyncMock(return_value=result_mock)

    status = await service.get_onboarding_status(1, 10, mock_db)

    assert status["user_id"] == 1
    assert status["completed"] is False
    assert status["rating_count"] == 3
    assert status["threshold"] == 10


@pytest.mark.asyncio
async def test_get_onboarding_status_completed(service, mock_db):
    """Status is completed when rating count >= threshold."""
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = 15
    mock_db.execute = AsyncMock(return_value=result_mock)

    status = await service.get_onboarding_status(1, 10, mock_db)

    assert status["completed"] is True
    assert status["rating_count"] == 15


@pytest.mark.asyncio
async def test_get_onboarding_status_exact_threshold(service, mock_db):
    """Status is completed when rating count equals threshold exactly."""
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = 10
    mock_db.execute = AsyncMock(return_value=result_mock)

    status = await service.get_onboarding_status(1, 10, mock_db)

    assert status["completed"] is True


@pytest.mark.asyncio
async def test_get_onboarding_movies_returns_empty_when_no_movies(service, mock_db):
    """Returns empty list when no qualifying movies exist."""
    # First call: per-genre query returns no IDs
    per_genre_result = MagicMock()
    per_genre_result.scalars.return_value.all.return_value = []
    # Second call: fill query returns no IDs
    fill_result = MagicMock()
    fill_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[per_genre_result, fill_result])

    movies = await service.get_onboarding_movies(1, 20, mock_db)

    assert movies == []


@pytest.mark.asyncio
async def test_get_onboarding_movies_returns_movies(service, mock_db):
    """Returns movie objects when qualifying movies exist."""
    # First call: per-genre query returns some IDs
    per_genre_result = MagicMock()
    per_genre_result.scalars.return_value.all.return_value = [1, 2, 3]
    # Second call: fill query returns more IDs
    fill_result = MagicMock()
    fill_result.scalars.return_value.all.return_value = [4, 5]
    # Third call: fetch full Movie objects
    movie1 = MagicMock()
    movie1.id = 1
    movie2 = MagicMock()
    movie2.id = 2
    movie3 = MagicMock()
    movie3.id = 3
    movie4 = MagicMock()
    movie4.id = 4
    movie5 = MagicMock()
    movie5.id = 5
    movies_result = MagicMock()
    movies_result.scalars.return_value.all.return_value = [
        movie1,
        movie2,
        movie3,
        movie4,
        movie5,
    ]
    mock_db.execute = AsyncMock(side_effect=[per_genre_result, fill_result, movies_result])

    movies = await service.get_onboarding_movies(1, 5, mock_db)

    assert len(movies) == 5
    mock_db.execute.assert_awaited()


@pytest.mark.asyncio
async def test_get_onboarding_movies_no_fill_when_genres_cover_count(service, mock_db):
    """No fill query when per-genre results already cover count."""
    per_genre_result = MagicMock()
    per_genre_result.scalars.return_value.all.return_value = [1, 2, 3]
    # No fill query needed — 3 genres for count=3
    movie1 = MagicMock()
    movie1.id = 1
    movie2 = MagicMock()
    movie2.id = 2
    movie3 = MagicMock()
    movie3.id = 3
    movies_result = MagicMock()
    movies_result.scalars.return_value.all.return_value = [movie1, movie2, movie3]
    mock_db.execute = AsyncMock(side_effect=[per_genre_result, movies_result])

    movies = await service.get_onboarding_movies(1, 3, mock_db)

    assert len(movies) == 3
    # Only 2 execute calls: per-genre + fetch (no fill)
    assert mock_db.execute.await_count == 2
