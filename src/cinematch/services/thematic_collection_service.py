"""Service for generating auto-curated thematic movie collections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.thematic_collection import (
    ThematicCollectionDetailResponse,
    ThematicCollectionMovieResult,
    ThematicCollectionsResponse,
    ThematicCollectionSummary,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.movie_service import MovieService


class ThematicCollectionService:
    """Generate on-demand thematic collections from existing movie data."""

    def __init__(self, movie_service: MovieService) -> None:
        self._movie_service = movie_service

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    async def list_collections(
        self,
        db: AsyncSession,
        *,
        collection_type: str | None = None,
    ) -> ThematicCollectionsResponse:
        """Return available thematic collections, optionally filtered by type."""
        results: list[ThematicCollectionSummary] = []

        if collection_type is None or collection_type == "genre_decade":
            results.extend(await self._genre_decade_catalog(db))

        if collection_type is None or collection_type == "director":
            results.extend(await self._director_catalog(db))

        if collection_type is None or collection_type == "year":
            results.extend(await self._year_catalog(db))

        return ThematicCollectionsResponse(
            results=results,
            collection_type=collection_type,
        )

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    async def get_collection(
        self,
        db: AsyncSession,
        *,
        collection_id: str,
        limit: int = 20,
    ) -> ThematicCollectionDetailResponse | None:
        """Fetch ranked movies for a specific collection."""
        if collection_id.startswith("genre_decade:"):
            return await self._genre_decade_detail(db, collection_id, limit)
        if collection_id.startswith("director:"):
            return await self._director_detail(db, collection_id, limit)
        if collection_id.startswith("year:"):
            return await self._year_detail(db, collection_id, limit)
        return None

    # ------------------------------------------------------------------
    # Genre-decade helpers
    # ------------------------------------------------------------------

    async def _genre_decade_catalog(self, db: AsyncSession) -> list[ThematicCollectionSummary]:
        counts = await self._movie_service.genre_decade_counts(db, min_count=5)
        summaries: list[ThematicCollectionSummary] = []
        for genre, decade, movie_count in counts:
            cid = f"genre_decade:{genre}:{decade}"
            title = f"Best {genre} of the {decade}s"
            posters = await self._movie_service.genre_decade_preview_posters(
                db, genre=genre, decade=decade, limit=4
            )
            summaries.append(
                ThematicCollectionSummary(
                    id=cid,
                    title=title,
                    collection_type="genre_decade",
                    movie_count=movie_count,
                    preview_posters=posters,
                )
            )
        return summaries

    async def _genre_decade_detail(
        self, db: AsyncSession, collection_id: str, limit: int
    ) -> ThematicCollectionDetailResponse | None:
        parts = collection_id.split(":", 2)
        if len(parts) != 3:
            return None
        genre = parts[1]
        try:
            decade = int(parts[2])
        except ValueError:
            return None

        rows = await self._movie_service.top_by_genre_decade(
            db, genre=genre, decade=decade, limit=limit
        )
        if not rows:
            return None

        return ThematicCollectionDetailResponse(
            id=collection_id,
            title=f"Best {genre} of the {decade}s",
            collection_type="genre_decade",
            results=[
                ThematicCollectionMovieResult(
                    movie=MovieSummary.model_validate(movie),
                    avg_rating=round(avg, 2),
                    rating_count=count,
                )
                for movie, avg, count in rows
            ],
            total=len(rows),
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Director helpers
    # ------------------------------------------------------------------

    async def _director_catalog(self, db: AsyncSession) -> list[ThematicCollectionSummary]:
        directors = await self._movie_service.popular_directors(db, limit=50)
        return [
            ThematicCollectionSummary(
                id=f"director:{name}",
                title=f"{name}: A Filmography",
                collection_type="director",
                movie_count=film_count,
                preview_posters=[],
            )
            for name, film_count, _avg in directors
        ]

    async def _director_detail(
        self, db: AsyncSession, collection_id: str, limit: int
    ) -> ThematicCollectionDetailResponse | None:
        name = collection_id.split(":", 1)[1]
        if not name:
            return None

        films, _stats = await self._movie_service.filmography_by_director(db, name=name)
        if not films:
            return None

        # Sort by vote_average descending, take top `limit`
        sorted_films = sorted(films, key=lambda f: f[0].vote_average, reverse=True)[:limit]

        return ThematicCollectionDetailResponse(
            id=collection_id,
            title=f"{name}: A Filmography",
            collection_type="director",
            results=[
                ThematicCollectionMovieResult(
                    movie=MovieSummary.model_validate(movie),
                    avg_rating=round(movie.vote_average, 2),
                    rating_count=movie.vote_count,
                )
                for movie, _user_rating in sorted_films
            ],
            total=len(films),
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Year helpers
    # ------------------------------------------------------------------

    async def _year_catalog(self, db: AsyncSession) -> list[ThematicCollectionSummary]:
        # Reuse decade stats and expand into individual years
        # For efficiency, use a raw query to get year-level stats
        from sqlalchemy import text

        stmt = text(
            "SELECT EXTRACT(YEAR FROM release_date)::int AS yr, COUNT(*)::int AS cnt "
            "FROM movies "
            "WHERE release_date IS NOT NULL "
            "GROUP BY yr "
            "HAVING COUNT(*) >= 10 "
            "ORDER BY yr DESC"
        )
        result = await db.execute(stmt)
        return [
            ThematicCollectionSummary(
                id=f"year:{yr}",
                title=f"Highest Rated {yr}",
                collection_type="year",
                movie_count=cnt,
                preview_posters=[],
            )
            for yr, cnt in result.all()
        ]

    async def _year_detail(
        self, db: AsyncSession, collection_id: str, limit: int
    ) -> ThematicCollectionDetailResponse | None:
        try:
            year = int(collection_id.split(":", 1)[1])
        except (ValueError, IndexError):
            return None

        rows = await self._movie_service.top_by_year(db, year=year, limit=limit)
        if not rows:
            return None

        return ThematicCollectionDetailResponse(
            id=collection_id,
            title=f"Highest Rated {year}",
            collection_type="year",
            results=[
                ThematicCollectionMovieResult(
                    movie=MovieSummary.model_validate(movie),
                    avg_rating=round(avg, 2),
                    rating_count=count,
                )
                for movie, avg, count in rows
            ],
            total=len(rows),
            limit=limit,
        )
