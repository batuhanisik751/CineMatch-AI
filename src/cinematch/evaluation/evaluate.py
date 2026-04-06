"""Full evaluation pipeline: split data, generate recommendations, compute metrics."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
import scipy.sparse as sp
from implicit.als import AlternatingLeastSquares

from cinematch.config import get_settings
from cinematch.core.pickle_safety import verify_and_log
from cinematch.evaluation.metrics import map_at_k, ndcg_at_k, precision_at_k, recall_at_k
from cinematch.evaluation.splitter import temporal_split


def _content_recommend(
    user_top_movies: list[int],
    faiss_index: faiss.Index,
    id_to_faiss_idx: dict[int, int],
    faiss_id_map: list[int],
    exclude: set[int],
    top_k: int,
) -> list[int]:
    """Content-based: find similar movies to user's favorites via FAISS."""
    candidates: dict[int, float] = {}
    for mid in user_top_movies:
        idx = id_to_faiss_idx.get(mid)
        if idx is None:
            continue
        query = faiss_index.reconstruct(idx).reshape(1, -1).astype(np.float32)
        distances, indices = faiss_index.search(query, top_k + 1)
        for dist, fidx in zip(distances[0], indices[0]):
            if fidx == -1:
                continue
            candidate = faiss_id_map[fidx]
            if candidate in exclude or candidate == mid:
                continue
            candidates[candidate] = max(candidates.get(candidate, 0.0), float(dist))

    ranked = sorted(candidates, key=candidates.get, reverse=True)
    return ranked[:top_k]


def _collab_recommend(
    user_id: int,
    model: AlternatingLeastSquares,
    user_map: dict[int, int],
    reverse_item_map: dict[int, int],
    user_items: sp.csr_matrix,
    exclude: set[int],
    top_k: int,
) -> list[int]:
    """Collaborative: ALS recommendations for a user."""
    user_idx = user_map.get(user_id)
    if user_idx is None:
        return []

    item_indices, _scores = model.recommend(
        user_idx, user_items[user_idx], N=top_k + len(exclude), filter_already_liked_items=True
    )
    results = []
    for iidx in item_indices:
        mid = reverse_item_map.get(int(iidx))
        if mid is not None and mid not in exclude:
            results.append(mid)
        if len(results) >= top_k:
            break
    return results


def run_evaluation(
    processed_dir: str | None = None,
    n_users: int = 1000,
    k_values: list[int] | None = None,
) -> dict:
    """Run full evaluation pipeline and return metrics dict."""
    if k_values is None:
        k_values = [5, 10, 20]

    settings = get_settings()
    processed_dir = Path(processed_dir or settings.data_processed_dir)

    # Load data
    print("Loading data...")
    ratings = pd.read_parquet(processed_dir / "ratings_clean.parquet")
    train, test = temporal_split(ratings, train_ratio=0.8)
    print(f"  Train: {len(train):,} ratings, Test: {len(test):,} ratings")

    # Load FAISS
    print("Loading FAISS index...")
    faiss_index = faiss.read_index(str(processed_dir / "faiss.index"))
    pkl_paths = [
        processed_dir / "faiss_id_map.pkl",
        processed_dir / "als_model.pkl",
        processed_dir / "als_user_map.pkl",
        processed_dir / "als_item_map.pkl",
    ]
    for pkl_path in pkl_paths:
        status = verify_and_log(pkl_path)
        if status == "mismatch":
            raise RuntimeError(f"Pickle integrity check FAILED for {pkl_path}. Aborting.")
    with open(processed_dir / "faiss_id_map.pkl", "rb") as f:
        faiss_id_map = pickle.load(f)  # noqa: S301  # nosec B301 - trusted local artifact
    id_to_faiss_idx = {mid: i for i, mid in enumerate(faiss_id_map)}

    # Load ALS
    print("Loading ALS model...")
    with open(processed_dir / "als_model.pkl", "rb") as f:
        als_model = pickle.load(f)  # noqa: S301  # nosec B301 - trusted local artifact
    with open(processed_dir / "als_user_map.pkl", "rb") as f:
        user_map = pickle.load(f)  # noqa: S301  # nosec B301 - trusted local artifact
    with open(processed_dir / "als_item_map.pkl", "rb") as f:
        item_map = pickle.load(f)  # noqa: S301  # nosec B301 - trusted local artifact
    reverse_item_map = {v: k for k, v in item_map.items()}
    user_items = sp.load_npz(str(processed_dir / "als_user_items.npz"))

    # Build test set: users with >= 5 highly-rated test items
    test_high = test[test["rating"] >= 8]
    user_counts = test_high.groupby("user_id").size()
    eligible_users = user_counts[user_counts >= 5].index.tolist()
    print(f"  Eligible users (>=5 high test ratings): {len(eligible_users):,}")

    rng = np.random.RandomState(42)
    sample_size = min(n_users, len(eligible_users))
    sampled_users = rng.choice(eligible_users, size=sample_size, replace=False)
    print(f"  Sampled users: {len(sampled_users)}")

    # Per-user train data: top-rated movies for content recs
    train_by_user = train.groupby("user_id")

    # Compute metrics
    strategies = ["content", "collab"]
    results: dict[str, dict[str, list[float]]] = {
        s: {f"{m}@{k}": [] for k in k_values for m in ["P", "R", "NDCG", "MAP"]} for s in strategies
    }

    max_k = max(k_values)

    for i, uid in enumerate(sampled_users):
        if (i + 1) % 100 == 0:
            print(f"  Evaluating user {i + 1}/{len(sampled_users)}...")

        relevant = set(test_high[test_high["user_id"] == uid]["movie_id"].tolist())
        train_rated = set()
        user_top_movies: list[int] = []

        if uid in train_by_user.groups:
            user_train = train_by_user.get_group(uid).sort_values("rating", ascending=False)
            train_rated = set(user_train["movie_id"].tolist())
            user_top_movies = user_train.head(10)["movie_id"].tolist()

        # Content recs
        content_recs = _content_recommend(
            user_top_movies,
            faiss_index,
            id_to_faiss_idx,
            faiss_id_map,
            exclude=train_rated,
            top_k=max_k,
        )

        # Collab recs
        collab_recs = _collab_recommend(
            uid,
            als_model,
            user_map,
            reverse_item_map,
            user_items,
            exclude=train_rated,
            top_k=max_k,
        )

        for strategy, recs in [("content", content_recs), ("collab", collab_recs)]:
            for k in k_values:
                results[strategy][f"P@{k}"].append(precision_at_k(recs, relevant, k))
                results[strategy][f"R@{k}"].append(recall_at_k(recs, relevant, k))
                results[strategy][f"NDCG@{k}"].append(ndcg_at_k(recs, relevant, k))
                results[strategy][f"MAP@{k}"].append(map_at_k(recs, relevant, k))

    # Average metrics
    report: dict[str, dict[str, float]] = {}
    for strategy in strategies:
        report[strategy] = {
            metric: round(float(np.mean(values)), 4) if values else 0.0
            for metric, values in results[strategy].items()
        }

    # Print table
    print("\n" + "=" * 80)
    print("Evaluation Results")
    print("=" * 80)
    header = f"{'Strategy':<12}"
    for k in k_values:
        header += f"{'P@' + str(k):>8}{'R@' + str(k):>8}{'NDCG@' + str(k):>10}{'MAP@' + str(k):>10}"
    print(header)
    print("-" * len(header))

    for strategy in strategies:
        row = f"{strategy:<12}"
        for k in k_values:
            row += f"{report[strategy][f'P@{k}']:>8.4f}"
            row += f"{report[strategy][f'R@{k}']:>8.4f}"
            row += f"{report[strategy][f'NDCG@{k}']:>10.4f}"
            row += f"{report[strategy][f'MAP@{k}']:>10.4f}"
        print(row)

    print("=" * 80)

    # Save JSON report
    report_path = processed_dir / "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")

    return report


if __name__ == "__main__":
    run_evaluation()
