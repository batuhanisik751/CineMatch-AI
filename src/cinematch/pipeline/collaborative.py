"""Train ALS collaborative filtering model using implicit."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from implicit.als import AlternatingLeastSquares

from cinematch.config import get_settings


def train_als(
    processed_dir: str | None = None,
    factors: int | None = None,
    iterations: int | None = None,
    regularization: float | None = None,
) -> None:
    """Train ALS model on user-item rating matrix and save artifacts."""
    settings = get_settings()
    processed_dir = Path(processed_dir or settings.data_processed_dir)
    factors = factors or settings.als_factors
    iterations = iterations or settings.als_iterations
    regularization = regularization or settings.als_regularization

    # Load ratings
    ratings_path = processed_dir / "ratings_clean.parquet"
    if not ratings_path.exists():
        raise FileNotFoundError(f"ratings_clean.parquet not found. Run cleaner first.")

    print(f"Loading ratings from {ratings_path}...")
    ratings = pd.read_parquet(ratings_path)
    print(f"  {len(ratings):,} ratings loaded.")

    # Build user and item mappings (ID -> matrix index)
    unique_users = sorted(ratings["user_id"].unique())
    unique_items = sorted(ratings["movie_id"].unique())

    user_map = {uid: idx for idx, uid in enumerate(unique_users)}
    item_map = {mid: idx for idx, mid in enumerate(unique_items)}

    n_users = len(unique_users)
    n_items = len(unique_items)
    print(f"  Users: {n_users:,}, Items: {n_items:,}")

    # Build sparse user-item matrix
    # Confidence = 1 + alpha * rating (alpha=40 is standard)
    print("Building sparse user-item matrix...")
    user_indices = np.array([user_map[uid] for uid in ratings["user_id"]])
    item_indices = np.array([item_map[mid] for mid in ratings["movie_id"]])
    confidence_values = (1 + 40 * ratings["rating"].values).astype(np.float32)

    user_items = sp.csr_matrix(
        (confidence_values, (user_indices, item_indices)),
        shape=(n_users, n_items),
    )
    print(f"  Matrix shape: {user_items.shape}, nnz: {user_items.nnz:,}")

    # Train ALS
    print(f"Training ALS (factors={factors}, iterations={iterations}, reg={regularization})...")
    model = AlternatingLeastSquares(
        factors=factors,
        iterations=iterations,
        regularization=regularization,
        random_state=42,
    )
    model.fit(user_items)
    print("  Training complete.")

    # Save artifacts
    print(f"Saving artifacts to {processed_dir}/...")

    model_path = Path(settings.als_model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"  als_model.pkl ({model_path.stat().st_size / 1024 / 1024:.1f} MB)")

    with open(settings.als_user_map_path, "wb") as f:
        pickle.dump(user_map, f)
    print(f"  als_user_map.pkl ({len(user_map):,} users)")

    with open(settings.als_item_map_path, "wb") as f:
        pickle.dump(item_map, f)
    print(f"  als_item_map.pkl ({len(item_map):,} items)")

    sp.save_npz(settings.als_user_items_path, user_items)
    print(f"  als_user_items.npz")

    print("[OK] ALS training complete.")


if __name__ == "__main__":
    train_als()
