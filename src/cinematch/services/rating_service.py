"""Rating service for managing user ratings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
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
