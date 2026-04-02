"""Rating service for managing user ratings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert

from cinematch.models.movie import Movie
from cinematch.models.rating import Rating
from cinematch.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RatingService:
    """Manage user ratings in the database."""

    async def add_rating(
        self,
        user_id: int,
        movie_id: int,
        rating: float,
        db: AsyncSession,
    ) -> Rating:
        """Insert or update a rating. Auto-creates user if not exists."""
        # Ensure user exists
        user_result = await db.execute(select(User).where(User.id == user_id))
        if user_result.scalar_one_or_none() is None:
            db.add(User(id=user_id, movielens_id=user_id))
            await db.flush()

        now = datetime.now(UTC)

        stmt = (
            insert(Rating)
            .values(user_id=user_id, movie_id=movie_id, rating=rating, timestamp=now)
            .on_conflict_do_update(
                constraint="uq_user_movie",
                set_={"rating": rating, "timestamp": now},
            )
            .returning(Rating)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one()

    async def get_user_ratings(
        self,
        user_id: int,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Rating, str | None]], int]:
        """Get paginated ratings for a user. Returns ([(rating, movie_title), ...], total_count)."""
        count_stmt = select(func.count()).select_from(Rating).where(Rating.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(Rating, Movie.title)
            .outerjoin(Movie, Rating.movie_id == Movie.id)
            .where(Rating.user_id == user_id)
            .order_by(Rating.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = [(rating, title) for rating, title in result.all()]
        return rows, total

    async def bulk_check(
        self,
        user_id: int,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> dict[int, int]:
        """Return {movie_id: rating} for movies the user has rated from the given list."""
        if not movie_ids:
            return {}
        stmt = select(Rating.movie_id, Rating.rating).where(
            Rating.user_id == user_id,
            Rating.movie_id.in_(movie_ids),
        )
        result = await db.execute(stmt)
        return {row[0]: int(row[1]) for row in result.all()}

    async def get_rated_movie_ids(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> set[int]:
        """Get all movie IDs the user has rated."""
        result = await db.execute(select(Rating.movie_id).where(Rating.user_id == user_id))
        return {r[0] for r in result.fetchall()}

    async def get_movie_rating_stats(
        self,
        movie_id: int,
        db: AsyncSession,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Get rating distribution stats for a movie, optionally including user's rating."""
        agg_result = await db.execute(
            text(
                "SELECT AVG(rating), "
                "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rating), "
                "COUNT(*), "
                "STDDEV_POP(rating) "
                "FROM ratings WHERE movie_id = :mid"
            ),
            {"mid": movie_id},
        )
        row = agg_result.one()
        avg_rating = round(float(row[0]), 2) if row[0] is not None else 0.0
        median_rating = round(float(row[1]), 2) if row[1] is not None else 0.0
        total_ratings = int(row[2])
        stddev = round(float(row[3]), 2) if row[3] is not None else 0.0
        # Max possible stddev for 1-10 range is 4.5 (half ratings at 1, half at 10)
        polarization_score = round(stddev / 4.5, 2) if total_ratings > 0 else 0.0

        dist_result = await db.execute(
            text("SELECT rating, COUNT(*) FROM ratings WHERE movie_id = :mid GROUP BY rating"),
            {"mid": movie_id},
        )
        counts = {int(r[0]): int(r[1]) for r in dist_result.all()}
        distribution = [{"rating": i, "count": counts.get(i, 0)} for i in range(1, 11)]

        user_rating = None
        if user_id is not None:
            ur_result = await db.execute(
                text("SELECT rating FROM ratings WHERE movie_id = :mid AND user_id = :uid"),
                {"mid": movie_id, "uid": user_id},
            )
            ur_row = ur_result.one_or_none()
            if ur_row is not None:
                user_rating = int(ur_row[0])

        return {
            "movie_id": movie_id,
            "avg_rating": avg_rating,
            "median_rating": median_rating,
            "total_ratings": total_ratings,
            "stddev": stddev,
            "polarization_score": polarization_score,
            "distribution": distribution,
            "user_rating": user_rating,
        }

    async def get_movie_activity(
        self,
        movie_id: int,
        granularity: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Get rating activity timeline for a movie, grouped by time period."""
        result = await db.execute(
            text(
                "SELECT DATE_TRUNC(:gran, timestamp) AS period, "
                "COUNT(*) AS rating_count, "
                "ROUND(AVG(rating)::numeric, 2) AS avg_rating "
                "FROM ratings WHERE movie_id = :mid "
                "GROUP BY 1 ORDER BY 1"
            ),
            {"gran": granularity, "mid": movie_id},
        )
        rows = result.all()

        fmt = "%Y-%m" if granularity == "month" else "%Y-W%W"
        timeline = [
            {
                "period": row[0].strftime(fmt),
                "rating_count": int(row[1]),
                "avg_rating": float(row[2]),
            }
            for row in rows
        ]
        total = sum(r["rating_count"] for r in timeline)

        return {
            "movie_id": movie_id,
            "granularity": granularity,
            "timeline": timeline,
            "total_ratings": total,
        }

    async def get_rating_stats_pair(
        self,
        movie_id1: int,
        movie_id2: int,
        db: AsyncSession,
    ) -> dict[int, tuple[float, int]]:
        """Get avg rating and count for two movies in one query."""
        result = await db.execute(
            text(
                "SELECT movie_id, AVG(rating), COUNT(*) "
                "FROM ratings WHERE movie_id IN (:m1, :m2) "
                "GROUP BY movie_id"
            ),
            {"m1": movie_id1, "m2": movie_id2},
        )
        stats: dict[int, tuple[float, int]] = {}
        for row in result.all():
            stats[int(row[0])] = (round(float(row[1]), 2), int(row[2]))
        return stats
