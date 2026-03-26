"""Temporal train/test split for evaluation."""

from __future__ import annotations

import pandas as pd


def temporal_split(
    ratings_df: pd.DataFrame,
    train_ratio: float = 0.8,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split ratings by timestamp: first train_ratio for training, rest for testing."""
    sorted_df = ratings_df.sort_values("timestamp").reset_index(drop=True)
    split_idx = int(len(sorted_df) * train_ratio)
    train = sorted_df.iloc[:split_idx]
    test = sorted_df.iloc[split_idx:]
    return train, test
