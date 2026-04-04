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


async def test_list_movies_runtime_min_filter(service, mock_db):
    """Filters by minimum runtime."""
    movie = _mock_movie()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.list_movies(mock_db, min_runtime=90)

    assert total == 1
    assert movies == [movie]
    assert mock_db.execute.call_count == 2


async def test_list_movies_runtime_max_filter(service, mock_db):
    """Filters by maximum runtime."""
    movie = _mock_movie()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.list_movies(mock_db, max_runtime=150)

    assert total == 1
    assert movies == [movie]
    assert mock_db.execute.call_count == 2


async def test_list_movies_runtime_range_filter(service, mock_db):
    """Filters by runtime range (min and max)."""
    movie = _mock_movie()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.list_movies(mock_db, min_runtime=90, max_runtime=150)

    assert total == 1
    assert movies == [movie]
    assert mock_db.execute.call_count == 2


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


# --- semantic_search tests ---


async def test_semantic_search_returns_movies_with_scores(service, mock_db):
    """Returns (Movie, similarity) tuples ordered by pgvector score."""
    movie1 = _mock_movie(id=1, title="Interstellar")
    movie2 = _mock_movie(id=2, title="Gravity")

    # pgvector query returns IDs and similarities
    pgvector_result = MagicMock()
    pgvector_result.fetchall.return_value = [(1, 0.92), (2, 0.85)]

    mock_db.execute = AsyncMock(return_value=pgvector_result)

    # Patch get_movies_by_ids via the service instance
    service.get_movies_by_ids = AsyncMock(return_value={1: movie1, 2: movie2})

    results = await service.semantic_search([0.1] * 384, mock_db, limit=20)

    assert len(results) == 2
    assert results[0] == (movie1, 0.92)
    assert results[1] == (movie2, 0.85)


async def test_semantic_search_empty_results(service, mock_db):
    """Returns empty list when pgvector finds no matches."""
    pgvector_result = MagicMock()
    pgvector_result.fetchall.return_value = []

    mock_db.execute = AsyncMock(return_value=pgvector_result)

    results = await service.semantic_search([0.1] * 384, mock_db)

    assert results == []


async def test_semantic_search_preserves_order(service, mock_db):
    """Results maintain pgvector similarity ordering, not ID ordering."""
    movie5 = _mock_movie(id=5, title="Movie 5")
    movie2 = _mock_movie(id=2, title="Movie 2")
    movie8 = _mock_movie(id=8, title="Movie 8")

    pgvector_result = MagicMock()
    pgvector_result.fetchall.return_value = [(5, 0.95), (8, 0.88), (2, 0.72)]

    mock_db.execute = AsyncMock(return_value=pgvector_result)
    service.get_movies_by_ids = AsyncMock(return_value={5: movie5, 2: movie2, 8: movie8})

    results = await service.semantic_search([0.1] * 384, mock_db)

    assert [r[0].id for r in results] == [5, 8, 2]
    assert [r[1] for r in results] == [0.95, 0.88, 0.72]


async def test_semantic_search_uses_typed_vector_binding(service, mock_db):
    """Verify query_embedding is passed as list, not str (pgvector type safety)."""
    pgvector_result = MagicMock()
    pgvector_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=pgvector_result)

    embedding = [0.1] * 384
    await service.semantic_search(embedding, mock_db)

    call_args = mock_db.execute.call_args
    params = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs
    assert isinstance(params["query_embedding"], list)
    assert not isinstance(params["query_embedding"], str)


# --- trending tests ---


async def test_trending_returns_movies_with_counts(service, mock_db):
    """Returns (Movie, count) tuples from aggregate + batch fetch."""
    movie1 = _mock_movie(id=1, title="Trending Movie 1")
    movie2 = _mock_movie(id=2, title="Trending Movie 2")

    agg_result = MagicMock()
    agg_result.all.return_value = [(1, 50), (2, 30)]

    mock_db.execute = AsyncMock(return_value=agg_result)
    service.get_movies_by_ids = AsyncMock(return_value={1: movie1, 2: movie2})

    results = await service.trending(mock_db)

    assert len(results) == 2
    assert results[0] == (movie1, 50)
    assert results[1] == (movie2, 30)


async def test_trending_empty_results(service, mock_db):
    """Returns empty list when no ratings exist in the window."""
    agg_result = MagicMock()
    agg_result.all.return_value = []

    mock_db.execute = AsyncMock(return_value=agg_result)
    service.get_movies_by_ids = AsyncMock()

    results = await service.trending(mock_db)

    assert results == []
    service.get_movies_by_ids.assert_not_called()


async def test_trending_preserves_order(service, mock_db):
    """Results ordered by rating count DESC, not by movie ID."""
    movie5 = _mock_movie(id=5, title="Movie 5")
    movie2 = _mock_movie(id=2, title="Movie 2")
    movie8 = _mock_movie(id=8, title="Movie 8")

    agg_result = MagicMock()
    agg_result.all.return_value = [(5, 100), (2, 80), (8, 60)]

    mock_db.execute = AsyncMock(return_value=agg_result)
    service.get_movies_by_ids = AsyncMock(return_value={5: movie5, 2: movie2, 8: movie8})

    results = await service.trending(mock_db)

    assert [r[0].id for r in results] == [5, 2, 8]
    assert [r[1] for r in results] == [100, 80, 60]


async def test_trending_custom_window_and_limit(service, mock_db):
    """Accepts custom window and limit parameters."""
    movie1 = _mock_movie(id=1, title="Movie 1")

    agg_result = MagicMock()
    agg_result.all.return_value = [(1, 25)]

    mock_db.execute = AsyncMock(return_value=agg_result)
    service.get_movies_by_ids = AsyncMock(return_value={1: movie1})

    results = await service.trending(mock_db, window=30, limit=5)

    assert len(results) == 1
    assert mock_db.execute.call_count == 1


# --- hidden_gems tests ---


async def test_hidden_gems_returns_filtered_movies(service, mock_db):
    """Returns movies matching vote_average/vote_count filters."""
    movie1 = _mock_movie(id=1, title="Hidden Gem 1")
    movie2 = _mock_movie(id=2, title="Hidden Gem 2")

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie1, movie2]

    mock_db.execute = AsyncMock(return_value=results_result)

    results = await service.hidden_gems(mock_db)

    assert len(results) == 2
    assert results[0] == movie1
    assert results[1] == movie2
    mock_db.execute.assert_called_once()


async def test_hidden_gems_with_genre_filter(service, mock_db):
    """Passes genre filter through to the query."""
    movie = _mock_movie(id=1, title="Genre Gem")

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(return_value=results_result)

    results = await service.hidden_gems(mock_db, genre="Drama")

    assert len(results) == 1
    assert results[0] == movie
    mock_db.execute.assert_called_once()


async def test_hidden_gems_empty_results(service, mock_db):
    """Returns empty list when no movies match the filters."""
    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(return_value=results_result)

    results = await service.hidden_gems(mock_db)

    assert results == []


async def test_hidden_gems_custom_params(service, mock_db):
    """Accepts custom min_rating, max_votes, and limit."""
    movie = _mock_movie(id=1, title="Custom Gem")

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(return_value=results_result)

    results = await service.hidden_gems(mock_db, min_rating=8.0, max_votes=50, limit=5)

    assert len(results) == 1
    mock_db.execute.assert_called_once()


# --- top_by_genre tests ---


async def test_top_by_genre_returns_tuples(service, mock_db):
    """Returns (Movie, float, int) tuples; execute called once."""
    movie1 = _mock_movie(id=1, title="Top Thriller")

    result_mock = MagicMock()
    result_mock.all.return_value = [(movie1, 8.7, 120)]
    mock_db.execute = AsyncMock(return_value=result_mock)

    results = await service.top_by_genre(mock_db, genre="Thriller")

    assert len(results) == 1
    assert results[0] == (movie1, 8.7, 120)
    mock_db.execute.assert_called_once()


async def test_top_by_genre_empty_results(service, mock_db):
    """Returns empty list when no movies match."""
    result_mock = MagicMock()
    result_mock.all.return_value = []
    mock_db.execute = AsyncMock(return_value=result_mock)

    results = await service.top_by_genre(mock_db, genre="Thriller")

    assert results == []


async def test_top_by_genre_respects_limit(service, mock_db):
    """Custom limit is forwarded; execute called once."""
    movie = _mock_movie(id=1, title="Top Action")

    result_mock = MagicMock()
    result_mock.all.return_value = [(movie, 9.0, 200)]
    mock_db.execute = AsyncMock(return_value=result_mock)

    results = await service.top_by_genre(mock_db, genre="Action", limit=5)

    assert len(results) == 1
    mock_db.execute.assert_called_once()


async def test_top_by_genre_preserves_order(service, mock_db):
    """Results are returned in DB-dictated order (highest avg first)."""
    movie1 = _mock_movie(id=1, title="Best Drama")
    movie2 = _mock_movie(id=2, title="Second Drama")

    result_mock = MagicMock()
    result_mock.all.return_value = [(movie1, 9.1, 300), (movie2, 8.5, 150)]
    mock_db.execute = AsyncMock(return_value=result_mock)

    results = await service.top_by_genre(mock_db, genre="Drama")

    assert len(results) == 2
    assert results[0][0] == movie1
    assert results[1][0] == movie2


async def test_top_by_genre_custom_min_ratings(service, mock_db):
    """Custom min_ratings is accepted; execute called once."""
    movie = _mock_movie(id=1, title="Indie Gem")

    result_mock = MagicMock()
    result_mock.all.return_value = [(movie, 8.2, 15)]
    mock_db.execute = AsyncMock(return_value=result_mock)

    results = await service.top_by_genre(mock_db, genre="Comedy", min_ratings=10)

    assert len(results) == 1


# --- seasonal tests ---


async def test_seasonal_returns_movies_for_october(service, mock_db):
    """Returns horror-themed movies for October."""
    movie1 = _mock_movie(id=1, title="Halloween")
    movie2 = _mock_movie(id=2, title="The Exorcist")

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie1, movie2]

    mock_db.execute = AsyncMock(return_value=results_result)

    movies, ctx = await service.seasonal(mock_db, month=10)

    assert len(movies) == 2
    assert ctx.month == 10
    assert ctx.season_name == "Spooky Season"
    assert "Horror" in ctx.genres


async def test_seasonal_returns_movies_for_december(service, mock_db):
    """Returns holiday-themed movies for December."""
    movie1 = _mock_movie(id=1, title="Home Alone")

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie1]

    mock_db.execute = AsyncMock(return_value=results_result)

    movies, ctx = await service.seasonal(mock_db, month=12)

    assert len(movies) == 1
    assert ctx.month == 12
    assert ctx.season_name == "Holiday Season"
    assert "christmas" in ctx.keywords


async def test_seasonal_empty_results(service, mock_db):
    """Returns empty list when no movies match."""
    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(return_value=results_result)

    movies, ctx = await service.seasonal(mock_db, month=3)

    assert movies == []
    assert ctx.month == 3


async def test_seasonal_respects_limit(service, mock_db):
    """Custom limit is passed through."""
    movie1 = _mock_movie(id=1, title="Movie 1")

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie1]

    mock_db.execute = AsyncMock(return_value=results_result)

    movies, ctx = await service.seasonal(mock_db, month=10, limit=5)

    assert len(movies) == 1
    assert mock_db.execute.call_count == 1


async def test_seasonal_summer_has_popularity_context(service, mock_db):
    """Summer months include min_popularity in context."""
    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(return_value=results_result)

    for month in (6, 7, 8):
        _, ctx = await service.seasonal(mock_db, month=month)
        assert ctx.min_popularity is not None
    assert mock_db.execute.call_count == 3
