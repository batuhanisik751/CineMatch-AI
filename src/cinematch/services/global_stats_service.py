"""Platform-wide aggregate statistics."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.models.movie import Movie
from cinematch.models.rating import Rating
from cinematch.models.user import User

# Minimum number of ratings a movie must have to qualify as "highest rated".
_MIN_RATINGS_FOR_HIGHEST = 50


class GlobalStatsService:
    """Compute platform-wide aggregate statistics."""

    async def get_global_stats(self, db: AsyncSession) -> dict[str, Any]:
        """Return global platform stats as a dict matching GlobalStatsResponse."""

        # A: total movies
        total_movies = (await db.execute(select(func.count(Movie.id)))).scalar_one()

        # B: total users
        total_users = (await db.execute(select(func.count(User.id)))).scalar_one()

        # C: total ratings + average rating
        rating_agg = (
            await db.execute(
                select(
                    func.count(Rating.id).label("total"),
                    func.coalesce(func.avg(Rating.rating), 0).label("avg"),
                )
            )
        ).one()
        total_ratings = int(rating_agg.total)
        avg_rating = round(float(rating_agg.avg), 2)

        # D: most rated movie (highest number of ratings)
        most_rated_row = (
            await db.execute(
                text(
                    "SELECT m.id, m.title, m.poster_path, m.vote_average, "
                    "       m.genres, m.release_date, "
                    "       COUNT(r.id)::int AS rating_count "
                    "FROM movies m "
                    "JOIN ratings r ON r.movie_id = m.id "
                    "GROUP BY m.id "
                    "ORDER BY COUNT(r.id) DESC "
                    "LIMIT 1"
                )
            )
        ).first()

        most_rated_movie = _row_to_movie_ref(most_rated_row) if most_rated_row else None

        # E: highest rated movie (best average, min threshold)
        highest_rated_row = (
            await db.execute(
                text(
                    "SELECT m.id, m.title, m.poster_path, m.vote_average, "
                    "       m.genres, m.release_date, "
                    "       COUNT(r.id)::int AS rating_count, "
                    "       AVG(r.rating)::float AS avg_user_rating "
                    "FROM movies m "
                    "JOIN ratings r ON r.movie_id = m.id "
                    "GROUP BY m.id "
                    "HAVING COUNT(r.id) >= :min_ratings "
                    "ORDER BY AVG(r.rating) DESC "
                    "LIMIT 1"
                ),
                {"min_ratings": _MIN_RATINGS_FOR_HIGHEST},
            )
        ).first()

        highest_rated_movie = (
            _row_to_movie_ref(highest_rated_row, include_avg=True) if highest_rated_row else None
        )

        # F: most active user
        most_active_row = (
            await db.execute(
                text(
                    "SELECT u.id, u.movielens_id, COUNT(r.id)::int AS rating_count "
                    "FROM users u "
                    "JOIN ratings r ON r.user_id = u.id "
                    "GROUP BY u.id "
                    "ORDER BY COUNT(r.id) DESC "
                    "LIMIT 1"
                )
            )
        ).first()

        most_active_user = (
            {
                "id": most_active_row.id,
                "movielens_id": most_active_row.movielens_id,
                "rating_count": most_active_row.rating_count,
            }
            if most_active_row
            else None
        )

        # G: ratings in the last 7 days
        ratings_this_week = (
            await db.execute(
                select(func.count(Rating.id)).where(
                    Rating.timestamp >= func.now() - text("INTERVAL '7 days'")
                )
            )
        ).scalar_one()

        return {
            "total_movies": total_movies,
            "total_users": total_users,
            "total_ratings": total_ratings,
            "avg_rating": avg_rating,
            "most_rated_movie": most_rated_movie,
            "highest_rated_movie": highest_rated_movie,
            "most_active_user": most_active_user,
            "ratings_this_week": int(ratings_this_week),
        }


def _row_to_movie_ref(row: Any, *, include_avg: bool = False) -> dict[str, Any]:
    """Convert a raw SQL row to a movie reference dict."""
    genres = row.genres
    if isinstance(genres, str):
        genres = json.loads(genres)

    ref: dict[str, Any] = {
        "id": row.id,
        "title": row.title,
        "poster_path": row.poster_path,
        "vote_average": float(row.vote_average),
        "genres": genres if genres else [],
        "release_date": str(row.release_date) if row.release_date else None,
        "rating_count": row.rating_count,
    }
    if include_avg:
        ref["avg_user_rating"] = round(float(row.avg_user_rating), 2)
    return ref
