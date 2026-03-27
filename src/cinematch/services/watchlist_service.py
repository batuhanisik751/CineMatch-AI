"""Watchlist service for managing user watchlists."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from cinematch.models.movie import Movie
from cinematch.models.user import User
from cinematch.models.watchlist import WatchlistItem

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WatchlistService:
    """Manage user watchlists in the database."""

    async def add_to_watchlist(
        self,
        user_id: int,
        movie_id: int,
        db: AsyncSession,
    ) -> WatchlistItem:
        """Add a movie to the user's watchlist. Idempotent — no error on duplicate."""
        # Ensure user exists
        user_result = await db.execute(select(User).where(User.id == user_id))
        if user_result.scalar_one_or_none() is None:
            db.add(User(id=user_id, movielens_id=user_id))
            await db.flush()

        now = datetime.now(UTC)

        # INSERT ... ON CONFLICT DO NOTHING (idempotent)
        stmt = (
            insert(WatchlistItem)
            .values(user_id=user_id, movie_id=movie_id, added_at=now)
            .on_conflict_do_nothing(constraint="uq_watchlist_user_movie")
        )
        await db.execute(stmt)
        await db.commit()

        # Fetch the row (existing or newly created)
        result = await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.movie_id == movie_id,
            )
        )
        return result.scalar_one()

    async def remove_from_watchlist(
        self,
        user_id: int,
        movie_id: int,
        db: AsyncSession,
    ) -> bool:
        """Remove a movie from the watchlist. Returns True if a row was deleted."""
        stmt = delete(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.movie_id == movie_id,
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    async def get_watchlist(
        self,
        user_id: int,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[
        list[tuple[WatchlistItem, str | None, str | None, list | None, float, str | None]],
        int,
    ]:
        """Get paginated watchlist with movie details.

        Returns ([(item, title, poster_path, genres, vote_average, release_date), ...], total).
        """
        count_stmt = (
            select(func.count()).select_from(WatchlistItem).where(WatchlistItem.user_id == user_id)
        )
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(
                WatchlistItem,
                Movie.title,
                Movie.poster_path,
                Movie.genres,
                Movie.vote_average,
                Movie.release_date,
            )
            .outerjoin(Movie, WatchlistItem.movie_id == Movie.id)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.added_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.all())
        return rows, total

    async def is_in_watchlist(
        self,
        user_id: int,
        movie_id: int,
        db: AsyncSession,
    ) -> bool:
        """Check if a movie is in the user's watchlist."""
        stmt = (
            select(func.count())
            .select_from(WatchlistItem)
            .where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.movie_id == movie_id,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one() > 0

    async def bulk_check(
        self,
        user_id: int,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> set[int]:
        """Return the subset of movie_ids that are in the user's watchlist."""
        if not movie_ids:
            return set()
        stmt = select(WatchlistItem.movie_id).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.movie_id.in_(movie_ids),
        )
        result = await db.execute(stmt)
        return {row[0] for row in result.all()}
