"""Collaborative filtering recommender using implicit ALS."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import scipy.sparse as sp
    from implicit.als import AlternatingLeastSquares


class CollabRecommender:
    """Recommend movies based on user-item collaborative filtering (ALS)."""

    def __init__(
        self,
        model: AlternatingLeastSquares,
        user_map: dict[int, int],
        item_map: dict[int, int],
        user_items: sp.csr_matrix,
    ) -> None:
        self._model = model
        self._user_map = user_map
        self._item_map = item_map
        self._user_items = user_items
        self._reverse_item_map: dict[int, int] = {v: k for k, v in item_map.items()}

    def recommend_for_user(
        self,
        user_id: int,
        top_k: int = 50,
    ) -> list[tuple[int, float]]:
        """Return ``(movie_id, score)`` ranked list. Empty for cold-start users."""
        if not self.is_known_user(user_id):
            return []

        user_idx = self._user_map[user_id]
        item_indices, scores = self._model.recommend(
            user_idx,
            self._user_items[user_idx],
            N=top_k,
            filter_already_liked_items=True,
        )

        results: list[tuple[int, float]] = []
        for item_idx, score in zip(item_indices, scores):
            mid = self._reverse_item_map.get(int(item_idx))
            if mid is not None:
                results.append((mid, float(score)))
        return results

    def score_items(
        self,
        user_id: int,
        movie_ids: list[int],
    ) -> dict[int, float]:
        """Score specific movies for a user via factor dot product."""
        if not self.is_known_user(user_id):
            return {}

        user_idx = self._user_map[user_id]
        user_factors = self._model.user_factors[user_idx]

        scores: dict[int, float] = {}
        for mid in movie_ids:
            item_idx = self._item_map.get(mid)
            if item_idx is not None:
                score = float(np.dot(user_factors, self._model.item_factors[item_idx]))
                scores[mid] = score
        return scores

    def is_known_user(self, user_id: int) -> bool:
        """Check if the user exists in the ALS training data."""
        return user_id in self._user_map
