"""Tests for MovieService search logic, including fuzzy fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.movie_service import MovieService


def _mock_movie(id: int = 1, title: str = "Cars") -> MagicMock:
    m = MagicMock()
    m.id = id
    m.title = title
    return m


@pytest.fixture()
def service():
    return MovieService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


async def test_search_ilike_returns_results_no_fuzzy(service, mock_db):
    """When ILIKE finds results, fuzzy fallback is NOT triggered."""
    movie = _mock_movie()

    # First execute: count query returns 1
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    # Second execute: results query returns [movie]
    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.search_by_title("Cars", mock_db)

    assert total == 1
    assert movies == [movie]
    # Only 2 calls: ILIKE count + ILIKE results. No fuzzy queries.
    assert mock_db.execute.call_count == 2


async def test_search_ilike_empty_triggers_fuzzy(service, mock_db):
    """When ILIKE returns 0, fuzzy fallback is triggered for queries >= 3 chars."""
    movie = _mock_movie(title="Cars")

    # Call 1: ILIKE count returns 0
    ilike_count = MagicMock()
    ilike_count.scalar_one.return_value = 0

    # Call 2: set_config for pg_trgm threshold
    set_config_result = MagicMock()

    # Call 3: fuzzy count returns 1
    fuzzy_count = MagicMock()
    fuzzy_count.scalar_one.return_value = 1

    # Call 4: fuzzy results
    fuzzy_row = (movie, 0.35)
    fuzzy_results = MagicMock()
    fuzzy_results.all.return_value = [fuzzy_row]

    mock_db.execute = AsyncMock(
        side_effect=[ilike_count, set_config_result, fuzzy_count, fuzzy_results]
    )

    movies, total = await service.search_by_title("Casr", mock_db)

    assert total == 1
    assert movies == [movie]
    # 4 calls: ILIKE count, set_config, fuzzy count, fuzzy results
    assert mock_db.execute.call_count == 4


async def test_search_short_query_skips_fuzzy(service, mock_db):
    """Queries shorter than 3 chars skip fuzzy fallback entirely."""
    # ILIKE count returns 0
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    mock_db.execute = AsyncMock(side_effect=[count_result])

    movies, total = await service.search_by_title("Up", mock_db)

    assert total == 0
    assert movies == []
    # Only 1 call: ILIKE count. No fuzzy since query is too short.
    assert mock_db.execute.call_count == 1


async def test_search_both_empty(service, mock_db):
    """When both ILIKE and fuzzy return 0, empty list is returned."""
    # ILIKE count returns 0
    ilike_count = MagicMock()
    ilike_count.scalar_one.return_value = 0

    # set_config
    set_config_result = MagicMock()

    # Fuzzy count returns 0
    fuzzy_count = MagicMock()
    fuzzy_count.scalar_one.return_value = 0

    # Fuzzy results empty
    fuzzy_results = MagicMock()
    fuzzy_results.all.return_value = []

    mock_db.execute = AsyncMock(
        side_effect=[ilike_count, set_config_result, fuzzy_count, fuzzy_results]
    )

    movies, total = await service.search_by_title("xyzzy", mock_db)

    assert total == 0
    assert movies == []


# --- list_movies tests ---


async def test_list_movies_no_filters(service, mock_db):
    """Returns movies sorted by popularity desc with no filters."""
    movie = _mock_movie()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.list_movies(mock_db)

    assert total == 1
    assert movies == [movie]
    assert mock_db.execute.call_count == 2


async def test_list_movies_genre_filter(service, mock_db):
    """Filters by genre using JSONB containment."""
    movie = _mock_movie()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.list_movies(mock_db, genre="Action")

    assert total == 1
    assert movies == [movie]
    assert mock_db.execute.call_count == 2


async def test_list_movies_year_range(service, mock_db):
    """Filters by year range."""
    movie = _mock_movie()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.list_movies(mock_db, year_min=2000, year_max=2020)

    assert total == 1
    assert movies == [movie]
    assert mock_db.execute.call_count == 2


async def test_list_movies_pagination(service, mock_db):
    """Respects offset and limit."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 50

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [_mock_movie()]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.list_movies(mock_db, offset=20, limit=10)

    assert total == 50
    assert len(movies) == 1


async def test_list_movies_sort_by_title(service, mock_db):
    """Sorts by title ascending."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [_mock_movie()]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.list_movies(mock_db, sort_by="title", sort_order="asc")

    assert total == 1
    assert len(movies) == 1


# --- get_genre_counts tests ---


async def test_get_genre_counts(service, mock_db):
    """Returns genre counts from raw SQL aggregation."""
    result_mock = MagicMock()
    result_mock.all.return_value = [("Action", 150), ("Comedy", 120)]

    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_genre_counts(mock_db)

    assert result == [("Action", 150), ("Comedy", 120)]
    mock_db.execute.assert_called_once()


async def test_get_genre_counts_empty(service, mock_db):
    """Returns empty list when no genres exist."""
    result_mock = MagicMock()
    result_mock.all.return_value = []

    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_genre_counts(mock_db)

    assert result == []
