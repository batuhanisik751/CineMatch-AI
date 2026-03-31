"""User statistics service for profile analytics."""

from __future__ import annotations

import math
from collections import defaultdict
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

    async def get_affinities(
        self, user_id: int, db: AsyncSession, *, limit: int = 15
    ) -> dict[str, Any]:
        """Return director/actor affinity rankings weighted by avg_rating * log(count+1)."""

        # Check if user has any ratings
        total_result = await db.execute(
            select(func.count(Rating.id)).where(Rating.user_id == user_id)
        )
        if total_result.scalar() == 0:
            return {"user_id": user_id, "directors": [], "actors": []}

        # --- Directors ---
        dir_agg_stmt = text(
            "SELECT m.director, AVG(r.rating)::float AS avg_r, COUNT(*)::int AS cnt "
            "FROM ratings r "
            "JOIN movies m ON r.movie_id = m.id "
            "WHERE r.user_id = :uid AND m.director IS NOT NULL "
            "GROUP BY m.director "
            "HAVING COUNT(*) >= 2 "
            "ORDER BY AVG(r.rating) * LN(COUNT(*) + 1) DESC "
            "LIMIT :lim"
        )
        dir_rows = (await db.execute(dir_agg_stmt, {"uid": user_id, "lim": limit})).all()

        directors = []
        for name, avg_r, cnt in dir_rows:
            films_stmt = text(
                "SELECT m.id, m.title, r.rating, m.poster_path "
                "FROM ratings r JOIN movies m ON r.movie_id = m.id "
                "WHERE r.user_id = :uid AND m.director = :dir "
                "ORDER BY r.rating DESC"
            )
            films = (await db.execute(films_stmt, {"uid": user_id, "dir": name})).all()
            directors.append(
                {
                    "name": name,
                    "role": "director",
                    "avg_rating": round(avg_r, 2),
                    "count": cnt,
                    "weighted_score": round(avg_r * math.log(cnt + 1), 2),
                    "films_rated": [
                        {"movie_id": f[0], "title": f[1], "rating": f[2], "poster_path": f[3]}
                        for f in films
                    ],
                }
            )

        # --- Actors ---
        act_agg_stmt = text(
            "SELECT actor, AVG(r.rating)::float AS avg_r, COUNT(*)::int AS cnt "
            "FROM ratings r "
            "JOIN movies m ON r.movie_id = m.id, "
            "jsonb_array_elements_text(m.cast_names) AS actor "
            "WHERE r.user_id = :uid "
            "GROUP BY actor "
            "HAVING COUNT(*) >= 2 "
            "ORDER BY AVG(r.rating) * LN(COUNT(*) + 1) DESC "
            "LIMIT :lim"
        )
        act_rows = (await db.execute(act_agg_stmt, {"uid": user_id, "lim": limit})).all()

        actors = []
        for name, avg_r, cnt in act_rows:
            films_stmt = text(
                "SELECT m.id, m.title, r.rating, m.poster_path "
                "FROM ratings r "
                "JOIN movies m ON r.movie_id = m.id, "
                "jsonb_array_elements_text(m.cast_names) AS a "
                "WHERE r.user_id = :uid AND a = :actor "
                "ORDER BY r.rating DESC"
            )
            films = (await db.execute(films_stmt, {"uid": user_id, "actor": name})).all()
            actors.append(
                {
                    "name": name,
                    "role": "actor",
                    "avg_rating": round(avg_r, 2),
                    "count": cnt,
                    "weighted_score": round(avg_r * math.log(cnt + 1), 2),
                    "films_rated": [
                        {"movie_id": f[0], "title": f[1], "rating": f[2], "poster_path": f[3]}
                        for f in films
                    ],
                }
            )

        return {"user_id": user_id, "directors": directors, "actors": actors}

    async def get_diary(self, user_id: int, year: int, db: AsyncSession) -> dict[str, Any]:
        """Return daily rating activity for a given year."""
        stmt = text(
            "SELECT DATE(r.timestamp) AS day, r.movie_id, m.title, r.rating "
            "FROM ratings r "
            "LEFT JOIN movies m ON r.movie_id = m.id "
            "WHERE r.user_id = :uid "
            "  AND EXTRACT(YEAR FROM r.timestamp) = :year "
            "ORDER BY day, r.timestamp"
        )
        result = await db.execute(stmt, {"uid": user_id, "year": year})
        rows = result.all()

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            date_str = row[0].isoformat()
            grouped[date_str].append({"id": row[1], "title": row[2], "rating": row[3]})

        days = [
            {"date": d, "count": len(movies), "movies": movies}
            for d, movies in sorted(grouped.items())
        ]

        return {
            "user_id": user_id,
            "year": year,
            "days": days,
            "total_ratings": sum(d["count"] for d in days),
        }
