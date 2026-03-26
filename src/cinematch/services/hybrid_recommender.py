"""Hybrid recommender combining content-based and collaborative filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.collab_recommender import CollabRecommender
    from cinematch.services.content_recommender import ContentRecommender


class HybridRecommender:
    """Combine content and collaborative scores with configurable alpha."""

    def __init__(
        self,
        content_recommender: ContentRecommender,
        collab_recommender: CollabRecommender,
        alpha: float = 0.5,
    ) -> None:
        self._content = content_recommender
        self._collab = collab_recommender
        self._alpha = alpha

    async def recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int = 20,
        strategy: str = "hybrid",
    ) -> list[tuple[int, float]]:
        """Main entry point. Strategy: 'hybrid', 'content', or 'collab'."""
        if strategy == "hybrid":
            return await self._hybrid_recommend(user_id, db, top_k)
        if strategy == "content":
            return await self._content_only_recommend(user_id, db, top_k)
        if strategy == "collab":
            return self._collab_only_recommend(user_id, top_k)
        raise ValueError(f"Unknown strategy: {strategy!r}. Use 'hybrid', 'content', or 'collab'.")

    async def _hybrid_recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Full hybrid: alpha * content + (1 - alpha) * collab."""
        alpha = self._alpha if self._collab.is_known_user(user_id) else 1.0

        if alpha == 1.0:
            return await self._content_only_recommend(user_id, db, top_k)

        # Step 1: collaborative candidates
        collab_results = self._collab.recommend_for_user(user_id, top_k=100)
        collab_scores: dict[int, float] = {mid: s for mid, s in collab_results}

        # Step 2: user's top-rated movies
        user_top = await self._get_user_top_rated(user_id, db, limit=10)
        if not user_top:
            # No ratings — rely solely on collab
            return collab_results[:top_k]

        # Step 3: content candidates from user's favorites
        content_raw: dict[int, list[float]] = {}
        for rated_movie_id, user_rating in user_top:
            similar = await self._content.get_similar_movies(rated_movie_id, db, top_k=30)
            weight = user_rating / 5.0
            for mid, similarity in similar:
                content_raw.setdefault(mid, []).append(similarity * weight)

        # Step 4: aggregate content scores
        content_scores: dict[int, float] = {
            mid: float(np.mean(sims)) for mid, sims in content_raw.items()
        }

        # Step 5: merge pools, exclude already-rated
        rated_ids = await self._get_user_rated_movie_ids(user_id, db)
        all_candidates = (set(collab_scores) | set(content_scores)) - rated_ids

        # Step 6: normalize
        collab_norm = self._min_max_normalize(collab_scores)
        content_norm = self._min_max_normalize(content_scores)

        # Step 7: compute hybrid scores
        results: list[tuple[int, float]] = []
        for mid in all_candidates:
            c_score = content_norm.get(mid, 0.0)
            f_score = collab_norm.get(mid, 0.0)
            hybrid = alpha * c_score + (1 - alpha) * f_score
            results.append((mid, round(hybrid, 4)))

        results.sort(key=lambda r: r[1], reverse=True)
        return results[:top_k]

    async def _content_only_recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Content-only: recommend based on user's top-rated movies."""
        user_top = await self._get_user_top_rated(user_id, db, limit=10)
        if not user_top:
            return []

        content_raw: dict[int, list[float]] = {}
        for rated_movie_id, user_rating in user_top:
            similar = await self._content.get_similar_movies(rated_movie_id, db, top_k=30)
            weight = user_rating / 5.0
            for mid, similarity in similar:
                content_raw.setdefault(mid, []).append(similarity * weight)

        content_scores = {mid: float(np.mean(sims)) for mid, sims in content_raw.items()}

        rated_ids = await self._get_user_rated_movie_ids(user_id, db)
        results = [
            (mid, round(score, 4)) for mid, score in content_scores.items() if mid not in rated_ids
        ]
        results.sort(key=lambda r: r[1], reverse=True)
        return results[:top_k]

    def _collab_only_recommend(
        self,
        user_id: int,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Collab-only: delegate to CollabRecommender."""
        return self._collab.recommend_for_user(user_id, top_k=top_k)

    async def _get_user_top_rated(
        self,
        user_id: int,
        db: AsyncSession,
        limit: int = 10,
    ) -> list[tuple[int, float]]:
        """Fetch user's highest-rated movies as ``(movie_id, rating)``."""
        result = await db.execute(
            text(
                "SELECT movie_id, rating FROM ratings "
                "WHERE user_id = :user_id "
                "ORDER BY rating DESC, timestamp DESC "
                "LIMIT :limit"
            ),
            {"user_id": user_id, "limit": limit},
        )
        return [(r[0], float(r[1])) for r in result.fetchall()]

    async def _get_user_rated_movie_ids(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> set[int]:
        """Get all movie IDs the user has rated."""
        result = await db.execute(
            text("SELECT movie_id FROM ratings WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        return {r[0] for r in result.fetchall()}

    @staticmethod
    def _min_max_normalize(scores: dict[int, float]) -> dict[int, float]:
        """Normalize scores to [0, 1]. Returns 0.5 for all if values are equal."""
        if not scores:
            return scores
        min_s = min(scores.values())
        max_s = max(scores.values())
        if max_s == min_s:
            return {k: 0.5 for k in scores}
        return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}
