"""Movie service for database queries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from cinematch.models.movie import Movie

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class MovieService:
    """Query movies from the database."""

    async def get_by_id(self, movie_id: int, db: AsyncSession) -> Movie | None:
        """Fetch a single movie by primary key."""
        result = await db.execute(select(Movie).where(Movie.id == movie_id))
        return result.scalar_one_or_none()

    async def search_by_title(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 20,
    ) -> tuple[list[Movie], int]:
        """Search movies by title using ILIKE. Returns (results, total_count)."""
        pattern = f"%{query}%"

        count_stmt = select(func.count()).select_from(Movie).where(Movie.title.ilike(pattern))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(Movie)
            .where(Movie.title.ilike(pattern))
            .order_by(Movie.popularity.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_movies_by_ids(
        self,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> dict[int, Movie]:
        """Batch fetch movies by IDs. Returns {movie_id: Movie}."""
        if not movie_ids:
            return {}
        stmt = select(Movie).where(Movie.id.in_(movie_ids))
        result = await db.execute(stmt)
        return {m.id: m for m in result.scalars().all()}
