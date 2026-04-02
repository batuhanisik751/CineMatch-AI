"""Tests for the seasonal context mapping module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cinematch.core.seasonal import SEASONAL_MAP, SeasonalContext, get_seasonal_context


def test_all_months_have_context():
    for month in range(1, 13):
        assert month in SEASONAL_MAP
        ctx = SEASONAL_MAP[month]
        assert isinstance(ctx, SeasonalContext)
        assert ctx.month == month


def test_each_context_has_required_fields():
    for month, ctx in SEASONAL_MAP.items():
        assert ctx.season_name
        assert ctx.theme_label
        assert len(ctx.keywords) > 0
        assert len(ctx.genres) > 0
        assert ctx.sort_field in ("popularity", "vote_average")


def test_get_seasonal_context_returns_correct_month():
    for month in range(1, 13):
        ctx = get_seasonal_context(month)
        assert ctx.month == month
        assert ctx is SEASONAL_MAP[month]


def test_get_seasonal_context_defaults_to_current_month():
    with patch("cinematch.core.seasonal.datetime") as mock_dt:
        mock_dt.now.return_value.month = 10
        ctx = get_seasonal_context()
        assert ctx.month == 10


def test_october_has_horror_keywords():
    ctx = SEASONAL_MAP[10]
    assert "horror" in ctx.keywords
    assert "halloween" in ctx.keywords
    assert "Horror" in ctx.genres


def test_december_has_holiday_keywords():
    ctx = SEASONAL_MAP[12]
    assert "christmas" in ctx.keywords
    assert "holiday" in ctx.keywords
    assert "Family" in ctx.genres


def test_february_has_romance():
    ctx = SEASONAL_MAP[2]
    assert "love" in ctx.keywords
    assert "Romance" in ctx.genres


def test_summer_months_have_min_popularity():
    for month in (5, 6, 7, 8):
        ctx = SEASONAL_MAP[month]
        assert ctx.min_popularity is not None
        assert ctx.min_popularity > 0


def test_non_summer_months_have_no_min_popularity():
    for month in (1, 2, 3, 9, 10, 11, 12):
        ctx = SEASONAL_MAP[month]
        assert ctx.min_popularity is None


def test_seasonal_context_is_frozen():
    ctx = SEASONAL_MAP[10]
    with pytest.raises(AttributeError):
        ctx.month = 5  # type: ignore[misc]
