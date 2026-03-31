"""Service for comparing a user's ratings against community averages."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RatingComparisonService:
    """Computes how a user's ratings compare to the community."""

    async def get_rating_comparison(
        self,
        user_id: int,
        db: AsyncSession,
        top_n: int = 5,
    ) -> dict[str, Any]:
        query = text("""
            SELECT
                r.movie_id,
                m.title,
                m.poster_path,
                r.rating AS user_rating,
                AVG(r2.rating) AS community_avg
            FROM ratings r
            JOIN movies m ON r.movie_id = m.id
            JOIN ratings r2 ON r.movie_id = r2.movie_id
            WHERE r.user_id = :uid
            GROUP BY r.movie_id, m.title, m.poster_path, r.rating
        """)

        result = await db.execute(query, {"uid": user_id})
        rows = result.all()

        if not rows:
            return {
                "user_id": user_id,
                "user_avg": 0.0,
                "community_avg": 0.0,
                "agreement_pct": 0.0,
                "total_rated": 0,
                "most_overrated": [],
                "most_underrated": [],
            }

        comparisons = []
        for row in rows:
            comm_avg = round(float(row.community_avg), 1)
            diff = round(row.user_rating - comm_avg, 1)
            comparisons.append(
                {
                    "movie_id": row.movie_id,
                    "title": row.title,
                    "poster_path": row.poster_path,
                    "user_rating": row.user_rating,
                    "community_avg": comm_avg,
                    "difference": diff,
                }
            )

        user_avg = round(sum(c["user_rating"] for c in comparisons) / len(comparisons), 1)
        community_avg = round(sum(c["community_avg"] for c in comparisons) / len(comparisons), 1)

        agree_count = sum(1 for c in comparisons if abs(c["difference"]) <= 1.5)
        agreement_pct = round((agree_count / len(comparisons)) * 100, 1)

        sorted_by_diff = sorted(comparisons, key=lambda c: c["difference"], reverse=True)
        most_overrated = sorted_by_diff[:top_n]
        most_underrated = sorted_by_diff[-top_n:][::-1]

        return {
            "user_id": user_id,
            "user_avg": user_avg,
            "community_avg": community_avg,
            "agreement_pct": agreement_pct,
            "total_rated": len(comparisons),
            "most_overrated": most_overrated,
            "most_underrated": most_underrated,
        }
