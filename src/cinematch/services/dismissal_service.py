"""Dismissal service for managing 'Not Interested' feedback."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from cinematch.models.dismissal import Dismissal
from cinematch.models.movie import Movie
from cinematch.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DismissalService:
    """Manage user dismissals in the database."""

    async def dismiss_movie(
        self,
        user_id: int,
        movie_id: int,
        db: AsyncSession,
    ) -> Dismissal:
        """Mark a movie as dismissed. Idempotent — no error on duplicate."""
        # Ensure user exists
        user_result = await db.execute(select(User).where(User.id == user_id))
        if user_result.scalar_one_or_none() is None:
            db.add(User(id=user_id, movielens_id=user_id))
            await db.flush()

        now = datetime.now(UTC)

        # INSERT ... ON CONFLICT DO NOTHING (idempotent)
        stmt = (
            insert(Dismissal)
            .values(user_id=user_id, movie_id=movie_id, dismissed_at=now)
            .on_conflict_do_nothing(constraint="uq_dismissal_user_movie")
        )
        await db.execute(stmt)
        await db.commit()

        # Fetch the row (existing or newly created)
        result = await db.execute(
            select(Dismissal).where(
                Dismissal.user_id == user_id,
                Dismissal.movie_id == movie_id,
            )
        )
        return result.scalar_one()

    async def undismiss_movie(
        self,
        user_id: int,
        movie_id: int,
        db: AsyncSession,
    ) -> bool:
        """Remove a dismissal. Returns True if a row was deleted."""
        stmt = delete(Dismissal).where(
            Dismissal.user_id == user_id,
            Dismissal.movie_id == movie_id,
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    async def get_dismissed_movie_ids(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> set[int]:
        """Get all movie IDs dismissed by the user."""
        result = await db.execute(select(Dismissal.movie_id).where(Dismissal.user_id == user_id))
        return {row[0] for row in result.all()}

    async def get_dismissals(
        self,
        user_id: int,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[
        list[tuple[Dismissal, str | None, str | None, list | None, float, str | None]],
        int,
    ]:
        """Get paginated dismissals with movie details.

        Returns ([(dismissal, title, poster_path, genres, vote_average, release_date), ...], total).
        """
        count_stmt = select(func.count()).select_from(Dismissal).where(Dismissal.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(
                Dismissal,
                Movie.title,
                Movie.poster_path,
                Movie.genres,
                Movie.vote_average,
                Movie.release_date,
            )
            .outerjoin(Movie, Dismissal.movie_id == Movie.id)
            .where(Dismissal.user_id == user_id)
            .order_by(Dismissal.dismissed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.all())
        return rows, total

    async def bulk_check(
        self,
        user_id: int,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> set[int]:
        """Return the subset of movie_ids that are dismissed by the user."""
        if not movie_ids:
            return set()
        stmt = select(Dismissal.movie_id).where(
            Dismissal.user_id == user_id,
            Dismissal.movie_id.in_(movie_ids),
        )
        result = await db.execute(stmt)
        return {row[0] for row in result.all()}
