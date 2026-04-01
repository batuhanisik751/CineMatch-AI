"""Tests for BingoService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.bingo_service import BingoService, _month_seed


@pytest.fixture()
def service():
    return BingoService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _pool_results(
    genres: list[str] | None = None,
    decades: list[int] | None = None,
    directors: list[str] | None = None,
    keywords: list[str] | None = None,
):
    """Return mock execute results for the 4 parameter pool queries."""
    genres = genres or [
        "Action",
        "Comedy",
        "Drama",
        "Horror",
        "Sci-Fi",
        "Thriller",
        "Romance",
        "Animation",
    ]
    decades = decades or [1970, 1980, 1990, 2000, 2010, 2020]
    directors = directors or [
        "Christopher Nolan",
        "Martin Scorsese",
        "Steven Spielberg",
        "Quentin Tarantino",
        "David Fincher",
        "Ridley Scott",
    ]
    keywords = keywords or [
        "time travel",
        "dystopia",
        "revenge",
        "friendship",
        "love",
        "war",
        "survival",
        "conspiracy",
    ]

    genre_result = MagicMock()
    genre_result.all.return_value = [(g,) for g in genres]

    decade_result = MagicMock()
    decade_result.all.return_value = [(d,) for d in decades]

    director_result = MagicMock()
    director_result.all.return_value = [(d,) for d in directors]

    keyword_result = MagicMock()
    keyword_result.all.return_value = [(k,) for k in keywords]

    return [genre_result, decade_result, director_result, keyword_result]


def _no_match_result():
    """Return a mock result with no rows."""
    result = MagicMock()
    result.first.return_value = None
    return result


def _match_result(movie_id: int):
    """Return a mock result with one matching row."""
    result = MagicMock()
    result.first.return_value = (movie_id,)
    return result


@pytest.mark.asyncio
async def test_deterministic_generation(service, mock_db):
    """Same seed produces identical cells."""
    pools1 = _pool_results()
    pools2 = _pool_results()
    # 4 pool queries + 24 progress queries per call
    no_matches = [_no_match_result() for _ in range(24)]
    mock_db.execute = AsyncMock(side_effect=pools1 + no_matches + pools2 + no_matches)

    r1 = await service.get_user_bingo(1, "2026-04", mock_db)
    r2 = await service.get_user_bingo(1, "2026-04", mock_db)

    labels1 = [c["label"] for c in r1["cells"]]
    labels2 = [c["label"] for c in r2["cells"]]
    assert labels1 == labels2


@pytest.mark.asyncio
async def test_different_seeds_different_cards(service, mock_db):
    """Different seeds should produce different cards."""
    pools1 = _pool_results()
    pools2 = _pool_results()
    no_matches = [_no_match_result() for _ in range(24)]
    mock_db.execute = AsyncMock(side_effect=pools1 + no_matches + pools2 + no_matches)

    r1 = await service.get_user_bingo(1, "2026-01", mock_db)
    r2 = await service.get_user_bingo(1, "2026-06", mock_db)

    labels1 = [c["label"] for c in r1["cells"]]
    labels2 = [c["label"] for c in r2["cells"]]
    assert labels1 != labels2


@pytest.mark.asyncio
async def test_25_cells_with_free_center(service, mock_db):
    """Card has exactly 25 cells with FREE at index 12."""
    no_matches = [_no_match_result() for _ in range(24)]
    mock_db.execute = AsyncMock(side_effect=_pool_results() + no_matches)

    result = await service.get_user_bingo(1, "2026-04", mock_db)

    assert len(result["cells"]) == 25
    indices = [c["index"] for c in result["cells"]]
    assert indices == list(range(25))

    free_cell = result["cells"][12]
    assert free_cell["template"] == "free"
    assert free_cell["label"] == "FREE"
    assert free_cell["completed"] is True


@pytest.mark.asyncio
async def test_no_duplicate_labels(service, mock_db):
    """No two cells should have the same label."""
    no_matches = [_no_match_result() for _ in range(24)]
    mock_db.execute = AsyncMock(side_effect=_pool_results() + no_matches)

    result = await service.get_user_bingo(1, "2026-04", mock_db)

    labels = [c["label"] for c in result["cells"] if c["template"] != "free"]
    assert len(labels) == len(set(labels))


@pytest.mark.asyncio
async def test_no_progress_no_completions(service, mock_db):
    """User with no ratings has only FREE completed."""
    no_matches = [_no_match_result() for _ in range(24)]
    mock_db.execute = AsyncMock(side_effect=_pool_results() + no_matches)

    result = await service.get_user_bingo(1, "2026-04", mock_db)

    assert result["total_completed"] == 1  # Only FREE
    for c in result["cells"]:
        if c["template"] != "free":
            assert c["completed"] is False
            assert c["movie_id"] is None


@pytest.mark.asyncio
async def test_progress_marks_cells(service, mock_db):
    """Matching ratings mark cells as completed."""
    pools = _pool_results()

    # We need to match cells based on their template order.
    # The service queries cells grouped by template type.
    # Simulate: first genre cell matches (movie_id=42), rest don't.
    mock_db.execute = AsyncMock(side_effect=pools)

    # First generate the card to know the cell order
    import random as stdlib_random

    rng = stdlib_random.Random(_month_seed("2026-04"))
    cells = service._build_cells(
        rng,
        {
            "genres": [
                "Action",
                "Comedy",
                "Drama",
                "Horror",
                "Sci-Fi",
                "Thriller",
                "Romance",
                "Animation",
            ],
            "decades": [1970, 1980, 1990, 2000, 2010, 2020],
            "directors": [
                "Christopher Nolan",
                "Martin Scorsese",
                "Steven Spielberg",
                "Quentin Tarantino",
                "David Fincher",
                "Ridley Scott",
            ],
            "keywords": [
                "time travel",
                "dystopia",
                "revenge",
                "friendship",
                "love",
                "war",
                "survival",
                "conspiracy",
            ],
        },
    )

    # Count non-free cells by template
    template_counts = {}
    for c in cells:
        if c["template"] != "free":
            template_counts[c["template"]] = template_counts.get(c["template"], 0) + 1

    # Build progress results: first cell of each template matches, rest don't
    progress_results = []
    first_seen = set()
    for c in cells:
        if c["template"] == "free":
            continue
        if c["template"] not in first_seen:
            first_seen.add(c["template"])
            progress_results.append(_match_result(42))
        else:
            progress_results.append(_no_match_result())

    mock_db.execute = AsyncMock(side_effect=_pool_results() + progress_results)
    result = await service.get_user_bingo(1, "2026-04", mock_db)

    # Should have FREE + one per template type completed
    completed = [c for c in result["cells"] if c["completed"]]
    assert len(completed) >= 2  # At least FREE + 1 match


def test_month_seed_deterministic():
    """Same input gives same seed."""
    assert _month_seed("2026-04") == _month_seed("2026-04")
    assert _month_seed("2026-04") != _month_seed("2026-05")


def test_check_lines_empty():
    """No completed lines when only FREE is done."""
    service = BingoService()
    cells = [{"completed": i == 12} for i in range(25)]
    lines = service._check_lines(cells)
    assert lines == []


def test_check_lines_row():
    """Completed row is detected."""
    service = BingoService()
    cells = [{"completed": False} for _ in range(25)]
    # Complete first row (indices 0-4)
    for i in range(5):
        cells[i]["completed"] = True
    lines = service._check_lines(cells)
    assert [0, 1, 2, 3, 4] in lines


def test_check_lines_column():
    """Completed column is detected."""
    service = BingoService()
    cells = [{"completed": False} for _ in range(25)]
    # Complete first column (indices 0, 5, 10, 15, 20)
    for i in range(0, 25, 5):
        cells[i]["completed"] = True
    lines = service._check_lines(cells)
    assert [0, 5, 10, 15, 20] in lines


def test_check_lines_diagonal():
    """Completed diagonal is detected."""
    service = BingoService()
    cells = [{"completed": False} for _ in range(25)]
    # Complete main diagonal (0, 6, 12, 18, 24)
    for i in [0, 6, 12, 18, 24]:
        cells[i]["completed"] = True
    lines = service._check_lines(cells)
    assert [0, 6, 12, 18, 24] in lines
