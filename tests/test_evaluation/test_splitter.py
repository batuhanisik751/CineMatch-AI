"""Tests for temporal train/test splitter."""

from __future__ import annotations

import pandas as pd
import pytest

from cinematch.evaluation.splitter import temporal_split


@pytest.fixture()
def sample_ratings():
    return pd.DataFrame(
        {
            "user_id": [1, 1, 2, 2, 1],
            "movie_id": [10, 20, 10, 30, 30],
            "rating": [4.0, 3.5, 5.0, 2.0, 4.5],
            "timestamp": pd.to_datetime(
                [
                    "2020-01-01",
                    "2020-06-01",
                    "2021-01-01",
                    "2021-06-01",
                    "2022-01-01",
                ]
            ),
        }
    )


def test_temporal_split_ratio(sample_ratings):
    train, test = temporal_split(sample_ratings, train_ratio=0.8)
    assert len(train) == 4
    assert len(test) == 1


def test_temporal_split_preserves_order(sample_ratings):
    train, test = temporal_split(sample_ratings, train_ratio=0.6)
    # Train should have earlier timestamps than test
    assert train["timestamp"].max() <= test["timestamp"].min()


def test_temporal_split_all_rows_present(sample_ratings):
    train, test = temporal_split(sample_ratings, train_ratio=0.6)
    assert len(train) + len(test) == len(sample_ratings)


def test_temporal_split_50_50(sample_ratings):
    train, test = temporal_split(sample_ratings, train_ratio=0.5)
    assert len(train) == 2
    assert len(test) == 3
