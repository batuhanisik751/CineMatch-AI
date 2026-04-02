"""Service for suggesting movies worth rewatching."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Thresholds for "classic" indicator
_CLASSIC_MIN_VOTE_COUNT = 1000
_CLASSIC_MIN_VOTE_AVG = 7.0


class RewatchService:
    """Suggest highly-rated movies from long ago that the user may want to revisit."""

    async def get_rewatch_suggestions(
        self,
        user_id: int,
        db: AsyncSession,
        *,
        limit: int = 10,
        min_rating: int = 8,
    ) -> dict[str, Any]:
        """Return rewatch suggestions matching RewatchResponse schema."""

        query = text("""
            SELECT
                m.id,
                m.title,
                m.genres,
                m.vote_average,
                m.release_date,
                m.poster_path,
                m.original_language,
                m.runtime,
                m.vote_count,
                r.rating AS user_rating,
                r.timestamp AS rated_at,
                EXTRACT(DAY FROM NOW() - r.timestamp)::int AS days_since_rated,
                CASE
                    WHEN m.vote_count >= :classic_votes AND m.vote_average >= :classic_avg
                    THEN true ELSE false
                END AS is_classic
            FROM ratings r
            JOIN movies m ON m.id = r.movie_id
            WHERE r.user_id = :uid
              AND r.rating >= :min_rating
            ORDER BY r.rating DESC, r.timestamp ASC
            LIMIT :lim
        """)

        result = await db.execute(
            query,
            {
                "uid": user_id,
                "min_rating": min_rating,
                "lim": limit,
                "classic_votes": _CLASSIC_MIN_VOTE_COUNT,
                "classic_avg": _CLASSIC_MIN_VOTE_AVG,
            },
        )
        rows = result.all()

        suggestions = []
        for row in rows:
            suggestions.append(
                {
                    "movie": {
                        "id": row.id,
                        "title": row.title,
                        "genres": row.genres or [],
                        "vote_average": row.vote_average,
                        "release_date": row.release_date,
                        "poster_path": row.poster_path,
                        "original_language": row.original_language,
                        "runtime": row.runtime,
                    },
                    "user_rating": row.user_rating,
                    "rated_at": row.rated_at,
                    "days_since_rated": row.days_since_rated,
                    "is_classic": row.is_classic,
                }
            )

        return {
            "user_id": user_id,
            "suggestions": suggestions,
            "total": len(suggestions),
        }
