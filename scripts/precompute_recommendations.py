"""Precompute collaborative filtering recommendations into the database.

Loads the trained ALS model, computes top-N recommendations for every
eligible user, and writes them to the ``recommendations_cache`` table.
Designed to run locally or in GitHub Actions (Phase 3).
"""

from __future__ import annotations

import math
import pickle
import time
from pathlib import Path
from typing import TYPE_CHECKING

import scipy.sparse as sp
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from cinematch.config import get_settings
from cinematch.core.pickle_safety import verify_and_log

if TYPE_CHECKING:
    from implicit.als import AlternatingLeastSquares

    from cinematch.config import Settings


def load_als_artifacts(
    settings: Settings,
) -> tuple[AlternatingLeastSquares, dict[int, int], dict[int, int], sp.csr_matrix]:
    """Load and verify ALS model artifacts.

    Raises ``RuntimeError`` on checksum mismatch, ``FileNotFoundError``
    if an artifact file is missing.
    """
    pkl_paths = [
        settings.als_model_path,
        settings.als_user_map_path,
        settings.als_item_map_path,
    ]
    for pkl_path in pkl_paths:
        status = verify_and_log(pkl_path)
        if status == "mismatch":
            raise RuntimeError(f"Checksum FAILED for {pkl_path}")
        if status == "missing_artifact":
            raise FileNotFoundError(f"Artifact not found: {pkl_path}")

    with open(settings.als_model_path, "rb") as f:
        model = pickle.load(f)  # noqa: S301
    with open(settings.als_user_map_path, "rb") as f:
        user_map: dict[int, int] = pickle.load(f)  # noqa: S301
    with open(settings.als_item_map_path, "rb") as f:
        item_map: dict[int, int] = pickle.load(f)  # noqa: S301

    npz_path = Path(settings.als_user_items_path)
    if not npz_path.exists():
        raise FileNotFoundError(f"Artifact not found: {npz_path}")
    user_items = sp.load_npz(npz_path)

    print(f"  ALS model loaded ({len(user_map):,} users, {len(item_map):,} items)")
    return model, user_map, item_map, user_items


def get_eligible_user_ids(session: Session, user_map: dict[int, int]) -> list[int]:
    """Return user IDs present in both the database and the ALS user_map."""
    result = session.execute(text("SELECT id FROM users"))
    db_user_ids = {row[0] for row in result.fetchall()}
    eligible = sorted(int(uid) for uid in db_user_ids & user_map.keys())
    return eligible


def get_valid_movie_ids(session: Session) -> set[int]:
    """Return all movie IDs currently in the database."""
    result = session.execute(text("SELECT id FROM movies"))
    return {row[0] for row in result.fetchall()}


def compute_user_recommendations(
    model: AlternatingLeastSquares,
    user_idx: int,
    user_items_row: sp.csr_matrix,
    reverse_item_map: dict[int, int],
    valid_movie_ids: set[int],
    top_k: int = 50,
) -> list[tuple[int, float]]:
    """Compute top-K recommendations for a single user.

    Pure function — no database access, no side effects.
    Returns ``[(movie_id, score), ...]`` filtered to valid DB movies.
    """
    item_indices, scores = model.recommend(
        user_idx,
        user_items_row,
        N=top_k,
        filter_already_liked_items=True,
    )

    results: list[tuple[int, float]] = []
    for item_idx, score in zip(item_indices, scores):
        movie_id = reverse_item_map.get(int(item_idx))
        score_f = float(score)
        if movie_id is not None and movie_id in valid_movie_ids and math.isfinite(score_f):
            results.append((movie_id, score_f))
    return results


def precompute_recommendations(
    processed_dir: str | None = None,
    batch_size: int = 500,
    top_k: int = 50,
) -> None:
    """Load ALS artifacts, compute recommendations, and write to the database."""
    settings = get_settings()
    engine = create_engine(settings.database_url_sync.get_secret_value(), pool_size=5, echo=False)

    print("Loading ALS artifacts...")
    model, user_map, item_map, user_items = load_als_artifacts(settings)
    reverse_item_map: dict[int, int] = {v: k for k, v in item_map.items()}

    with Session(engine) as session:
        print("Querying eligible users and valid movies...")
        eligible_users = get_eligible_user_ids(session, user_map)
        valid_movie_ids = get_valid_movie_ids(session)
        skipped = len(user_map) - len(eligible_users)

        print(f"  Eligible users: {len(eligible_users):,}")
        print(f"  Valid movies: {len(valid_movie_ids):,}")
        if skipped > 0:
            print(f"  Users in ALS but not in DB: {skipped:,}")

        if not eligible_users:
            print("No eligible users found. Nothing to do.")
            return

        total_users = len(eligible_users)
        total_rows = 0
        start_time = time.time()

        for batch_start in range(0, total_users, batch_size):
            batch_end = min(batch_start + batch_size, total_users)
            batch_user_ids = eligible_users[batch_start:batch_end]

            # Compute recommendations for the batch
            all_rows: list[tuple[int, int, float]] = []
            for user_id in batch_user_ids:
                user_idx = user_map[user_id]
                recs = compute_user_recommendations(
                    model,
                    user_idx,
                    user_items[user_idx],
                    reverse_item_map,
                    valid_movie_ids,
                    top_k,
                )
                for movie_id, score in recs:
                    all_rows.append((user_id, movie_id, score))

            if all_rows:
                # DELETE old collaborative rows for this batch of users
                session.execute(
                    text(
                        "DELETE FROM recommendations_cache "
                        "WHERE strategy = 'collaborative' "
                        "AND user_id = ANY(:uids)"
                    ),
                    {"uids": batch_user_ids},
                )

                # Bulk INSERT new rows
                values_parts = [
                    f"({uid}, {mid}, {score}, 'collaborative', NOW())"
                    for uid, mid, score in all_rows
                ]
                # Insert in sub-batches of 5000 rows to avoid overly large statements
                sub_batch = 5000
                for i in range(0, len(values_parts), sub_batch):
                    chunk = values_parts[i : i + sub_batch]
                    session.execute(
                        text(
                            "INSERT INTO recommendations_cache "
                            "(user_id, movie_id, score, strategy, computed_at) "
                            f"VALUES {', '.join(chunk)}"
                        )
                    )

                session.commit()
                total_rows += len(all_rows)

            elapsed = time.time() - start_time
            rate = batch_end / elapsed if elapsed > 0 else 0
            if (batch_end % 5000 == 0) or batch_end == total_users:
                print(f"  Users: {batch_end:,}/{total_users:,} ({rate:.0f} users/s)")

        elapsed = time.time() - start_time
        print("\n=== Precomputation Complete ===")
        print(f"  Users processed: {total_users:,}")
        print(f"  Recommendations written: {total_rows:,}")
        if skipped > 0:
            print(f"  Users skipped (not in DB): {skipped:,}")
        print(f"  Time: {elapsed:.1f}s ({elapsed / 60:.1f}m)")


if __name__ == "__main__":
    precompute_recommendations()
