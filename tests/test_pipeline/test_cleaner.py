"""Tests for the TMDb cleaner cast-parsing logic."""

from __future__ import annotations

import pandas as pd

from cinematch.pipeline.cleaner import load_tmdb


def _minimal_tmdb_csv(tmp_path, cast_value: str) -> pd.DataFrame:
    """Create a minimal TMDB CSV with one row and the given cast string."""
    df = pd.DataFrame(
        {
            "id": [1],
            "imdb_id": ["tt0000001"],
            "title": ["Test Movie"],
            "overview": ["A test movie."],
            "genres": ["Action, Drama"],
            "cast": [cast_value],
            "director": ["John Doe"],
            "release_date": ["2020-01-01"],
            "vote_average": [7.5],
            "vote_count": [100],
            "popularity": [50.0],
            "poster_path": ["/test.jpg"],
            "original_language": ["en"],
            "runtime": [120],
            "tagline": ["A tagline"],
            "budget": [1000000],
            "revenue": [5000000],
        }
    )
    path = tmp_path / "TMDB_all_movies.csv"
    df.to_csv(path, index=False)
    return path


def test_cast_keeps_all_members(tmp_path):
    """All cast members are retained without slicing."""
    cast_str = ", ".join(f"Actor {i}" for i in range(20))
    path = _minimal_tmdb_csv(tmp_path, cast_str)
    result = load_tmdb(path)
    assert len(result["cast_names"].iloc[0]) == 20


def test_cast_filters_empty_strings_from_trailing_comma(tmp_path):
    """Trailing commas do not produce empty-string entries."""
    path = _minimal_tmdb_csv(tmp_path, "Alice, Bob, ")
    result = load_tmdb(path)
    assert result["cast_names"].iloc[0] == ["Alice", "Bob"]


def test_cast_empty_string_returns_empty_list(tmp_path):
    """An empty cast field yields an empty list."""
    path = _minimal_tmdb_csv(tmp_path, "")
    result = load_tmdb(path)
    assert result["cast_names"].iloc[0] == []


def test_cast_whitespace_only_returns_empty_list(tmp_path):
    """A whitespace-only cast field yields an empty list."""
    path = _minimal_tmdb_csv(tmp_path, "   ")
    result = load_tmdb(path)
    assert result["cast_names"].iloc[0] == []
