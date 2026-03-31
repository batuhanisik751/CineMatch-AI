"""Service for computing taste evolution over time."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TasteEvolutionService:
    """Compute genre distribution per time period for a user."""

    async def get_taste_evolution(
        self,
        user_id: int,
        db: AsyncSession,
        *,
        granularity: str = "quarter",
    ) -> dict[str, Any]:
        """Return taste evolution data matching TasteEvolutionResponse."""

        query = text("""
            WITH genre_ratings AS (
                SELECT
                    CASE
                        WHEN :gran = 'quarter' THEN TO_CHAR(r.timestamp, 'YYYY-"Q"Q')
                        WHEN :gran = 'month'   THEN TO_CHAR(r.timestamp, 'YYYY-MM')
                        WHEN :gran = 'year'    THEN TO_CHAR(r.timestamp, 'YYYY')
                    END AS period,
                    g.genre,
                    COUNT(*) AS cnt
                FROM ratings r
                JOIN movies m ON r.movie_id = m.id
                CROSS JOIN LATERAL jsonb_array_elements_text(m.genres) AS g(genre)
                WHERE r.user_id = :uid
                GROUP BY period, g.genre
            )
            SELECT
                period,
                genre,
                ROUND(100.0 * cnt / SUM(cnt) OVER (PARTITION BY period), 1) AS pct
            FROM genre_ratings
            ORDER BY period, pct DESC
        """)

        result = await db.execute(query, {"uid": user_id, "gran": granularity})
        rows = result.all()

        if not rows:
            return {
                "user_id": user_id,
                "granularity": granularity,
                "periods": [],
            }

        # Reshape: group rows by period
        periods_map: dict[str, dict[str, float]] = defaultdict(dict)
        for row in rows:
            periods_map[row.period][row.genre] = float(row.pct)

        periods = [
            {"period": period, "genres": genres} for period, genres in sorted(periods_map.items())
        ]

        return {
            "user_id": user_id,
            "granularity": granularity,
            "periods": periods,
        }
