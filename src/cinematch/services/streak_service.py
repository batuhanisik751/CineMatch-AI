"""Service for computing rating streaks and milestones."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_MILESTONES = [10, 25, 50, 100, 250, 500, 1000]


class StreakService:
    """Compute consecutive-day rating streaks and milestone badges."""

    async def get_streaks(self, user_id: int, db: AsyncSession) -> dict[str, Any]:
        """Return streak and milestone data matching StreakResponse."""

        # Total ratings count
        count_result = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM ratings WHERE user_id = :uid"),
            {"uid": user_id},
        )
        total_ratings = int(count_result.scalar_one())

        if total_ratings == 0:
            return {
                "user_id": user_id,
                "current_streak": 0,
                "longest_streak": 0,
                "total_ratings": 0,
                "milestones": [
                    {"threshold": t, "reached": False, "label": f"{t} Ratings"} for t in _MILESTONES
                ],
            }

        # Consecutive-date grouping via window function
        streak_query = text("""
            WITH rating_dates AS (
                SELECT DISTINCT DATE(timestamp AT TIME ZONE 'UTC') AS d
                FROM ratings
                WHERE user_id = :uid
            ),
            grouped AS (
                SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d))::int AS grp
                FROM rating_dates
            )
            SELECT
                MIN(d) AS streak_start,
                MAX(d) AS streak_end,
                COUNT(*)::int AS streak_len
            FROM grouped
            GROUP BY grp
            ORDER BY streak_end DESC
        """)
        result = await db.execute(streak_query, {"uid": user_id})
        rows = result.all()

        # Longest streak across all groups
        longest_streak = max(row.streak_len for row in rows) if rows else 0

        # Current streak: most recent group ending today or yesterday
        current_streak = 0
        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)
        if rows:
            most_recent = rows[0]  # ordered by streak_end DESC
            end_date = most_recent.streak_end
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            if end_date >= yesterday:
                current_streak = most_recent.streak_len

        milestones = [
            {"threshold": t, "reached": total_ratings >= t, "label": f"{t} Ratings"}
            for t in _MILESTONES
        ]

        return {
            "user_id": user_id,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_ratings": total_ratings,
            "milestones": milestones,
        }
