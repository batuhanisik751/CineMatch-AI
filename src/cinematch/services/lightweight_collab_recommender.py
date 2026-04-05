"""Lightweight collaborative recommender reading from recommendations_cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class LightweightCollabRecommender:
    """Read precomputed collaborative recommendations from the database.

    Drop-in replacement for ``CollabRecommender`` in lightweight mode.
    All methods are async and require a ``db`` session parameter.
    """

    async def recommend_for_user(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int = 50,
    ) -> list[tuple[int, float]]:
        """Return ``(movie_id, score)`` from the recommendations cache."""
        result = await db.execute(
            text(
                "SELECT movie_id, score FROM recommendations_cache "
                "WHERE user_id = :uid AND strategy = 'collaborative' "
                "ORDER BY score DESC LIMIT :top_k"
            ),
            {"uid": user_id, "top_k": top_k},
        )
        return [(row[0], float(row[1])) for row in result.fetchall()]

    async def score_items(
        self,
        user_id: int,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> dict[int, float]:
        """Look up precomputed scores for specific movies."""
        if not movie_ids:
            return {}
        result = await db.execute(
            text(
                "SELECT movie_id, score FROM recommendations_cache "
                "WHERE user_id = :uid AND strategy = 'collaborative' "
                "AND movie_id = ANY(:mids)"
            ),
            {"uid": user_id, "mids": movie_ids},
        )
        return {row[0]: float(row[1]) for row in result.fetchall()}

    async def is_known_user(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> bool:
        """Check if the user has precomputed recommendations."""
        result = await db.execute(
            text(
                "SELECT EXISTS("
                "SELECT 1 FROM recommendations_cache "
                "WHERE user_id = :uid AND strategy = 'collaborative'"
                ")"
            ),
            {"uid": user_id},
        )
        return bool(result.scalar())
