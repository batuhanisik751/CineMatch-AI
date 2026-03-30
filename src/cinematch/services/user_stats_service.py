"""User statistics service for profile analytics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, text

from cinematch.models.movie import Movie
from cinematch.models.rating import Rating

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# All possible integer rating buckets (1–10).
_RATING_BUCKETS = [str(v) for v in range(1, 11)]


class UserStatsService:
    """Compute aggregated analytics for a user's rating history."""

    async def get_user_stats(self, user_id: int, db: AsyncSession) -> dict[str, Any]:
        """Return all profile stats as a dict matching UserStatsResponse."""

        # A: Total ratings + average
        result = await db.execute(
            select(
                func.count(Rating.id).label("total"),
                func.coalesce(func.avg(Rating.rating), 0).label("average"),
            ).where(Rating.user_id == user_id)
        )
        row = result.one()
        total_ratings = int(row.total)
        average_rating = round(float(row.average), 2)

        if total_ratings == 0:
            return {
                "user_id": user_id,
                "total_ratings": 0,
                "average_rating": 0.0,
                "genre_distribution": [],
                "rating_distribution": [{"rating": b, "count": 0} for b in _RATING_BUCKETS],
                "top_directors": [],
                "top_actors": [],
                "rating_timeline": [],
            }

        # B: Genre distribution
        genre_stmt = text(
            "SELECT genre, COUNT(*)::int AS cnt "
            "FROM ratings r "
            "JOIN movies m ON r.movie_id = m.id, "
            "jsonb_array_elements_text(m.genres) AS genre "
            "WHERE r.user_id = :uid "
            "GROUP BY genre "
            "ORDER BY cnt DESC"
        )
        genre_result = await db.execute(genre_stmt, {"uid": user_id})
        genre_rows = genre_result.all()
        genre_total = sum(r[1] for r in genre_rows)
        genre_distribution = [
            {
                "genre": r[0],
                "count": r[1],
                "percentage": round(r[1] / genre_total * 100, 1) if genre_total else 0.0,
            }
            for r in genre_rows
        ]

        # C: Rating distribution
        rating_result = await db.execute(
            select(Rating.rating, func.count(Rating.id).label("cnt"))
            .where(Rating.user_id == user_id)
            .group_by(Rating.rating)
            .order_by(Rating.rating)
        )
        rating_map = {str(int(r.rating)): int(r.cnt) for r in rating_result.all()}
        rating_distribution = [
            {"rating": b, "count": rating_map.get(b, 0)} for b in _RATING_BUCKETS
        ]

        # D: Top directors
        director_result = await db.execute(
            select(Movie.director, func.count(Rating.id).label("cnt"))
            .join(Rating, Rating.movie_id == Movie.id)
            .where(Rating.user_id == user_id, Movie.director.isnot(None))
            .group_by(Movie.director)
            .order_by(func.count(Rating.id).desc())
            .limit(10)
        )
        top_directors = [{"name": r.director, "count": int(r.cnt)} for r in director_result.all()]

        # E: Top actors
        actor_stmt = text(
            "SELECT actor, COUNT(*)::int AS cnt "
            "FROM ratings r "
            "JOIN movies m ON r.movie_id = m.id, "
            "jsonb_array_elements_text(m.cast_names) AS actor "
            "WHERE r.user_id = :uid "
            "GROUP BY actor "
            "ORDER BY cnt DESC "
            "LIMIT 10"
        )
        actor_result = await db.execute(actor_stmt, {"uid": user_id})
        top_actors = [{"name": r[0], "count": r[1]} for r in actor_result.all()]

        # F: Rating timeline (monthly)
        timeline_stmt = text(
            "SELECT TO_CHAR(timestamp, 'YYYY-MM') AS month, COUNT(*)::int AS cnt "
            "FROM ratings "
            "WHERE user_id = :uid "
            "GROUP BY month "
            "ORDER BY month"
        )
        timeline_result = await db.execute(timeline_stmt, {"uid": user_id})
        rating_timeline = [{"month": r[0], "count": r[1]} for r in timeline_result.all()]

        return {
            "user_id": user_id,
            "total_ratings": total_ratings,
            "average_rating": average_rating,
            "genre_distribution": genre_distribution,
            "rating_distribution": rating_distribution,
            "top_directors": top_directors,
            "top_actors": top_actors,
            "rating_timeline": rating_timeline,
        }
