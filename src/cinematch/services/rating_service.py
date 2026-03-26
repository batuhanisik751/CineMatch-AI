"""Rating service for managing user ratings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

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
    ) -> tuple[list[Rating], int]:
        """Get paginated ratings for a user. Returns (ratings, total_count)."""
        count_stmt = select(func.count()).select_from(Rating).where(Rating.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(Rating)
            .where(Rating.user_id == user_id)
            .order_by(Rating.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total
