"""Movie service for database queries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import cast, desc, extract, func, select, text
from sqlalchemy.dialects.postgresql import JSONB as JSONB_TYPE

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
        """Search movies by title. Tries ILIKE first, falls back to pg_trgm fuzzy match."""
        pattern = f"%{query}%"

        # Fast path: exact substring match via ILIKE
        count_stmt = select(func.count()).select_from(Movie).where(Movie.title.ilike(pattern))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        if total > 0:
            stmt = (
                select(Movie)
                .where(Movie.title.ilike(pattern))
                .order_by(Movie.popularity.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            return list(result.scalars().all()), total

        # Fuzzy fallback: use pg_trgm similarity (skip for very short queries)
        if len(query) < 3:
            return [], 0

        await db.execute(text("SELECT set_config('pg_trgm.similarity_threshold', '0.2', true)"))

        similarity_col = func.similarity(Movie.title, query).label("sim")
        fuzzy_filter = Movie.title.op("%")(query)

        count_stmt = select(func.count()).select_from(Movie).where(fuzzy_filter)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(Movie, similarity_col)
            .where(fuzzy_filter)
            .order_by(desc("sim"), Movie.popularity.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        movies = [row[0] for row in result.all()]
        return movies, total

    async def list_movies(
        self,
        db: AsyncSession,
        *,
        genre: str | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        sort_by: str = "popularity",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Movie], int]:
        """List movies with optional genre/year filters, sorting, and pagination."""
        filters = []
        if genre is not None:
            filters.append(Movie.genres.op("@>")(cast([genre], JSONB_TYPE)))
        if year_min is not None:
            filters.append(extract("year", Movie.release_date) >= year_min)
        if year_max is not None:
            filters.append(extract("year", Movie.release_date) <= year_max)

        count_stmt = select(func.count()).select_from(Movie)
        for f in filters:
            count_stmt = count_stmt.where(f)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        sort_column_map = {
            "popularity": Movie.popularity,
            "vote_average": Movie.vote_average,
            "release_date": Movie.release_date,
            "title": Movie.title,
        }
        col = sort_column_map.get(sort_by, Movie.popularity)
        order = col.asc() if sort_order == "asc" else col.desc()

        stmt = select(Movie)
        for f in filters:
            stmt = stmt.where(f)
        stmt = stmt.order_by(order).offset(offset).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_genre_counts(self, db: AsyncSession) -> list[tuple[str, int]]:
        """Return all genres with their movie counts, ordered by count descending."""
        stmt = text(
            "SELECT genre, COUNT(*)::int AS count "
            "FROM movies, jsonb_array_elements_text(genres) AS genre "
            "GROUP BY genre "
            "ORDER BY count DESC"
        )
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

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
