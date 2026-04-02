"""Movie service for database queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import Integer, cast, desc, extract, func, outerjoin, select, text
from sqlalchemy.dialects.postgresql import JSONB as JSONB_TYPE

from cinematch.models.movie import Movie
from cinematch.models.rating import Rating

if TYPE_CHECKING:
    from collections import Counter

    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.content_recommender import ContentRecommender


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

    async def autocomplete(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 8,
    ) -> list[tuple]:
        """Lightweight autocomplete: returns (id, title, release_date, poster_path) tuples."""
        pattern = f"%{query}%"
        cols = (Movie.id, Movie.title, Movie.release_date, Movie.poster_path)

        stmt = (
            select(*cols)
            .where(Movie.title.ilike(pattern))
            .order_by(Movie.popularity.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()

        if rows:
            return rows

        if len(query) < 3:
            return []

        await db.execute(text("SELECT set_config('pg_trgm.similarity_threshold', '0.2', true)"))
        stmt = (
            select(*cols)
            .where(Movie.title.op("%")(query))
            .order_by(func.similarity(Movie.title, query).desc(), Movie.popularity.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.all()

    async def list_movies(
        self,
        db: AsyncSession,
        *,
        genre: str | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        language: str | None = None,
        min_runtime: int | None = None,
        max_runtime: int | None = None,
        sort_by: str = "popularity",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Movie], int]:
        """List movies with optional filters, sorting, and pagination."""
        filters = []
        if genre is not None:
            filters.append(Movie.genres.op("@>")(cast([genre], JSONB_TYPE)))
        if year_min is not None:
            filters.append(extract("year", Movie.release_date) >= year_min)
        if year_max is not None:
            filters.append(extract("year", Movie.release_date) <= year_max)
        if language is not None:
            filters.append(Movie.original_language == language)
        if min_runtime is not None:
            filters.append(Movie.runtime >= min_runtime)
        if max_runtime is not None:
            filters.append(Movie.runtime <= max_runtime)

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

    async def get_language_counts(self, db: AsyncSession) -> list[tuple[str, int]]:
        """Return all languages with their movie counts, ordered by count descending."""
        stmt = text(
            "SELECT original_language, COUNT(*)::int AS count "
            "FROM movies "
            "WHERE original_language IS NOT NULL AND original_language != '' "
            "GROUP BY original_language "
            "ORDER BY count DESC"
        )
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def semantic_search(
        self,
        query_embedding: list[float],
        db: AsyncSession,
        limit: int = 20,
    ) -> list[tuple[Movie, float]]:
        """Search movies by embedding similarity using pgvector."""
        result = await db.execute(
            text(
                "SELECT id, (embedding <#> :query_embedding) * -1 AS similarity "
                "FROM movies "
                "WHERE embedding IS NOT NULL "
                "ORDER BY embedding <#> :query_embedding "
                "LIMIT :limit"
            ),
            {"query_embedding": str(query_embedding), "limit": limit},
        )
        rows = result.fetchall()
        if not rows:
            return []

        id_score_map = {row[0]: float(row[1]) for row in rows}
        ordered_ids = [row[0] for row in rows]

        movies_map = await self.get_movies_by_ids(ordered_ids, db)
        return [(movies_map[mid], id_score_map[mid]) for mid in ordered_ids if mid in movies_map]

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

    async def trending(
        self,
        db: AsyncSession,
        *,
        window: int = 7,
        limit: int = 20,
    ) -> list[tuple[Movie, int]]:
        """Return the most-rated movies within the last `window` days."""
        cutoff = datetime.now(UTC) - timedelta(days=window)
        stmt = (
            select(Rating.movie_id, func.count().label("cnt"))
            .where(Rating.timestamp > cutoff)
            .group_by(Rating.movie_id)
            .order_by(desc("cnt"))
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return []

        id_count = {row[0]: row[1] for row in rows}
        ordered_ids = [row[0] for row in rows]
        movies_map = await self.get_movies_by_ids(ordered_ids, db)
        return [(movies_map[mid], id_count[mid]) for mid in ordered_ids if mid in movies_map]

    async def hidden_gems(
        self,
        db: AsyncSession,
        *,
        min_rating: float = 7.5,
        max_votes: int = 100,
        genre: str | None = None,
        limit: int = 20,
    ) -> list[Movie]:
        """Return high-quality movies that most users haven't found yet."""
        filters = [
            Movie.vote_average >= min_rating,
            Movie.vote_count <= max_votes,
            Movie.vote_count > 0,
        ]
        if genre is not None:
            filters.append(Movie.genres.op("@>")(cast([genre], JSONB_TYPE)))

        stmt = select(Movie)
        for f in filters:
            stmt = stmt.where(f)
        stmt = stmt.order_by(desc(Movie.vote_average), desc(Movie.vote_count)).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def top_by_genre(
        self,
        db: AsyncSession,
        *,
        genre: str,
        min_ratings: int = 50,
        limit: int = 20,
    ) -> list[tuple[Movie, float, int]]:
        """Return top-rated movies for a genre, ranked by in-system average rating."""
        avg_rating_col = func.avg(Rating.rating).label("avg_rating")
        rating_count_col = func.count(Rating.id).label("rating_count")

        stmt = (
            select(Movie, avg_rating_col, rating_count_col)
            .join(Rating, Rating.movie_id == Movie.id)
            .where(Movie.genres.op("@>")(cast([genre], JSONB_TYPE)))
            .group_by(Movie.id)
            .having(func.count(Rating.id) >= min_ratings)
            .order_by(desc(avg_rating_col))
            .limit(limit)
        )

        result = await db.execute(stmt)
        return [(row[0], float(row[1]), int(row[2])) for row in result.all()]

    async def get_decade_stats(
        self,
        db: AsyncSession,
    ) -> list[tuple[int, int, float]]:
        """Return available decades with movie count and average vote_average."""
        decade_col = (
            (func.floor(extract("year", Movie.release_date) / 10) * 10)
            .cast(Integer)
            .label("decade")
        )

        stmt = (
            select(
                decade_col,
                func.count().label("movie_count"),
                func.avg(Movie.vote_average).label("avg_rating"),
            )
            .where(Movie.release_date.isnot(None))
            .group_by(decade_col)
            .order_by(desc(decade_col))
        )
        result = await db.execute(stmt)
        return [(int(row[0]), int(row[1]), float(row[2])) for row in result.all()]

    async def top_by_decade(
        self,
        db: AsyncSession,
        *,
        decade: int,
        genre: str | None = None,
        min_ratings: int = 10,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Movie, float, int]], int]:
        """Return top-rated movies for a decade, ranked by in-system avg rating."""
        year_min = decade
        year_max = decade + 9

        filters = [
            extract("year", Movie.release_date) >= year_min,
            extract("year", Movie.release_date) <= year_max,
        ]
        if genre is not None:
            filters.append(Movie.genres.op("@>")(cast([genre], JSONB_TYPE)))

        # Count query
        count_stmt = select(func.count()).select_from(
            select(Movie.id)
            .join(Rating, Rating.movie_id == Movie.id)
            .where(*filters)
            .group_by(Movie.id)
            .having(func.count(Rating.id) >= min_ratings)
            .subquery()
        )
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        avg_rating_col = func.avg(Rating.rating).label("avg_rating")
        rating_count_col = func.count(Rating.id).label("rating_count")

        stmt = (
            select(Movie, avg_rating_col, rating_count_col)
            .join(Rating, Rating.movie_id == Movie.id)
            .where(*filters)
            .group_by(Movie.id)
            .having(func.count(Rating.id) >= min_ratings)
            .order_by(desc(avg_rating_col))
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = [(row[0], float(row[1]), int(row[2])) for row in result.all()]
        return rows, total

    async def search_directors(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[tuple[str, int, float]]:
        """Search directors by partial name match."""
        pattern = f"%{query}%"
        stmt = (
            select(
                Movie.director,
                func.count().label("film_count"),
                func.avg(Movie.vote_average).label("avg_vote"),
            )
            .where(Movie.director.isnot(None), Movie.director.ilike(pattern))
            .group_by(Movie.director)
            .order_by(desc("film_count"))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [(row[0], int(row[1]), float(row[2])) for row in result.all()]

    async def popular_directors(
        self,
        db: AsyncSession,
        limit: int = 30,
    ) -> list[tuple[str, int, float]]:
        """Return popular directors with at least 3 films, ordered by avg popularity."""
        stmt = (
            select(
                Movie.director,
                func.count().label("film_count"),
                func.avg(Movie.vote_average).label("avg_vote"),
            )
            .where(Movie.director.isnot(None))
            .group_by(Movie.director)
            .having(func.count() >= 3)
            .order_by(desc(func.avg(Movie.popularity)))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [(row[0], int(row[1]), float(row[2])) for row in result.all()]

    async def filmography_by_director(
        self,
        db: AsyncSession,
        *,
        name: str,
        user_id: int | None = None,
    ) -> tuple[list[tuple[Movie, float | None]], dict]:
        """Return a director's filmography with optional user rating overlay."""
        director_filter = func.lower(Movie.director) == func.lower(name)

        if user_id is not None:
            user_rating_col = Rating.rating.label("user_rating")
            stmt = (
                select(Movie, user_rating_col)
                .select_from(
                    outerjoin(
                        Movie,
                        Rating,
                        (Rating.movie_id == Movie.id) & (Rating.user_id == user_id),
                    )
                )
                .where(director_filter)
                .order_by(Movie.release_date.asc().nulls_last())
            )
            result = await db.execute(stmt)
            rows = result.all()
            films = [(row[0], float(row[1]) if row[1] is not None else None) for row in rows]
        else:
            stmt = (
                select(Movie).where(director_filter).order_by(Movie.release_date.asc().nulls_last())
            )
            result = await db.execute(stmt)
            films = [(m, None) for m in result.scalars().all()]

        # Compute stats
        all_genres: set[str] = set()
        vote_sum = 0.0
        user_ratings: list[float] = []
        for movie, user_rating in films:
            vote_sum += movie.vote_average
            all_genres.update(movie.genres or [])
            if user_rating is not None:
                user_ratings.append(user_rating)

        total_films = len(films)
        stats = {
            "total_films": total_films,
            "avg_vote": round(vote_sum / total_films, 2) if total_films > 0 else 0.0,
            "genres": sorted(all_genres),
            "user_avg_rating": (
                round(sum(user_ratings) / len(user_ratings), 2) if user_ratings else None
            ),
            "user_rated_count": len(user_ratings),
        }

        return films, stats

    async def search_actors(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[tuple[str, int, float]]:
        """Search actors by partial name match across cast_names JSONB arrays."""
        pattern = f"%{query}%"
        actor_name = func.jsonb_array_elements_text(Movie.cast_names).label("actor_name")
        unnested = (
            select(actor_name, Movie.vote_average)
            .where(Movie.cast_names != cast("[]", JSONB_TYPE))
            .subquery()
        )
        stmt = (
            select(
                unnested.c.actor_name,
                func.count().label("film_count"),
                func.avg(unnested.c.vote_average).label("avg_vote"),
            )
            .where(unnested.c.actor_name.ilike(pattern))
            .group_by(unnested.c.actor_name)
            .order_by(desc("film_count"))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [(row[0], int(row[1]), float(row[2])) for row in result.all()]

    async def popular_actors(
        self,
        db: AsyncSession,
        limit: int = 30,
    ) -> list[tuple[str, int, float]]:
        """Return popular actors with at least 3 films, ordered by avg popularity."""
        actor_name = func.jsonb_array_elements_text(Movie.cast_names).label("actor_name")
        unnested = (
            select(actor_name, Movie.vote_average, Movie.popularity)
            .where(Movie.cast_names != cast("[]", JSONB_TYPE))
            .subquery()
        )
        stmt = (
            select(
                unnested.c.actor_name,
                func.count().label("film_count"),
                func.avg(unnested.c.vote_average).label("avg_vote"),
            )
            .group_by(unnested.c.actor_name)
            .having(func.count() >= 3)
            .order_by(desc(func.avg(unnested.c.popularity)))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [(row[0], int(row[1]), float(row[2])) for row in result.all()]

    async def filmography_by_actor(
        self,
        db: AsyncSession,
        *,
        name: str,
        user_id: int | None = None,
    ) -> tuple[list[tuple[Movie, float | None]], dict]:
        """Return an actor's filmography with optional user rating overlay."""
        actor_filter = Movie.cast_names.op("@>")(func.jsonb_build_array(name).cast(JSONB_TYPE))

        if user_id is not None:
            user_rating_col = Rating.rating.label("user_rating")
            stmt = (
                select(Movie, user_rating_col)
                .select_from(
                    outerjoin(
                        Movie,
                        Rating,
                        (Rating.movie_id == Movie.id) & (Rating.user_id == user_id),
                    )
                )
                .where(actor_filter)
                .order_by(Movie.release_date.asc().nulls_last())
            )
            result = await db.execute(stmt)
            rows = result.all()
            films = [(row[0], float(row[1]) if row[1] is not None else None) for row in rows]
        else:
            stmt = select(Movie).where(actor_filter).order_by(Movie.release_date.asc().nulls_last())
            result = await db.execute(stmt)
            films = [(m, None) for m in result.scalars().all()]

        # Compute stats
        all_genres: set[str] = set()
        vote_sum = 0.0
        user_ratings: list[float] = []
        for movie, user_rating in films:
            vote_sum += movie.vote_average
            all_genres.update(movie.genres or [])
            if user_rating is not None:
                user_ratings.append(user_rating)

        total_films = len(films)
        stats = {
            "total_films": total_films,
            "avg_vote": round(vote_sum / total_films, 2) if total_films > 0 else 0.0,
            "genres": sorted(all_genres),
            "user_avg_rating": (
                round(sum(user_ratings) / len(user_ratings), 2) if user_ratings else None
            ),
            "user_rated_count": len(user_ratings),
        }

        return films, stats

    async def popular_keywords(
        self,
        db: AsyncSession,
        limit: int = 50,
        min_count: int = 5,
    ) -> list[tuple[str, int]]:
        """Return most frequent keywords with their movie counts."""
        stmt = text(
            "SELECT keyword, COUNT(*)::int AS count "
            "FROM movies, jsonb_array_elements_text(keywords) AS keyword "
            "GROUP BY keyword "
            "HAVING COUNT(*) >= :min_count "
            "ORDER BY count DESC "
            "LIMIT :limit"
        )
        result = await db.execute(stmt, {"min_count": min_count, "limit": limit})
        return [(row[0], row[1]) for row in result.all()]

    async def search_keywords(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[tuple[str, int]]:
        """Search keywords by partial name match."""
        pattern = f"%{query}%"
        stmt = text(
            "SELECT keyword, COUNT(*)::int AS count "
            "FROM movies, jsonb_array_elements_text(keywords) AS keyword "
            "WHERE keyword ILIKE :pattern "
            "GROUP BY keyword "
            "ORDER BY count DESC "
            "LIMIT :limit"
        )
        result = await db.execute(stmt, {"pattern": pattern, "limit": limit})
        return [(row[0], row[1]) for row in result.all()]

    async def movies_by_keyword(
        self,
        db: AsyncSession,
        *,
        keyword: str,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Movie], int, dict]:
        """Return movies containing a specific keyword with stats."""
        keyword_filter = Movie.keywords.op("@>")(cast([keyword], JSONB_TYPE))

        # Count query
        count_stmt = select(func.count()).select_from(Movie).where(keyword_filter)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = (
            select(Movie)
            .where(keyword_filter)
            .order_by(Movie.popularity.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        movies = list(result.scalars().all())

        # Stats
        avg_stmt = select(func.avg(Movie.vote_average)).where(keyword_filter)
        avg_result = await db.execute(avg_stmt)
        avg_vote = avg_result.scalar_one() or 0.0

        # Top genres among matching movies
        genre_stmt = text(
            "SELECT genre, COUNT(*)::int AS cnt "
            "FROM movies, jsonb_array_elements_text(genres) AS genre "
            "WHERE movies.keywords @> CAST(:kw_array AS jsonb) "
            "GROUP BY genre ORDER BY cnt DESC LIMIT 5"
        )
        genre_result = await db.execute(genre_stmt, {"kw_array": f'["{keyword}"]'})
        top_genres = [row[0] for row in genre_result.all()]

        stats = {
            "total_movies": total,
            "avg_vote": round(float(avg_vote), 2),
            "top_genres": top_genres,
        }

        return movies, total, stats

    async def surprise_movies(
        self,
        db: AsyncSession,
        *,
        excluded_genres: list[str],
        excluded_movie_ids: list[int] | None = None,
        min_rating: float = 7.0,
        limit: int = 5,
    ) -> list[Movie]:
        """Return random well-rated movies outside the given genres."""
        filters = [Movie.vote_average > min_rating, Movie.vote_count > 0]
        for genre in excluded_genres:
            filters.append(~Movie.genres.op("@>")(cast([genre], JSONB_TYPE)))
        if excluded_movie_ids:
            filters.append(~Movie.id.in_(excluded_movie_ids))

        stmt = select(Movie)
        for f in filters:
            stmt = stmt.where(f)
        stmt = stmt.order_by(func.random()).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def advanced_search(
        self,
        db: AsyncSession,
        *,
        genre: str | None = None,
        decade: str | None = None,
        min_rating: float | None = None,
        max_rating: float | None = None,
        director: str | None = None,
        keyword: str | None = None,
        cast_name: str | None = None,
        language: str | None = None,
        min_runtime: int | None = None,
        max_runtime: int | None = None,
        sort_by: str = "popularity",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Movie], int]:
        """Advanced multi-criteria movie search with dynamic filter chaining."""
        filters = []
        if genre is not None:
            filters.append(Movie.genres.op("@>")(cast([genre], JSONB_TYPE)))
        if decade is not None:
            decade_start = int(decade[:-1])
            filters.append(extract("year", Movie.release_date) >= decade_start)
            filters.append(extract("year", Movie.release_date) <= decade_start + 9)
        if min_rating is not None:
            filters.append(Movie.vote_average >= min_rating)
        if max_rating is not None:
            filters.append(Movie.vote_average <= max_rating)
        if director is not None:
            filters.append(Movie.director.ilike(f"%{director}%"))
        if keyword is not None:
            filters.append(Movie.keywords.op("@>")(cast([keyword], JSONB_TYPE)))
        if cast_name is not None:
            filters.append(
                Movie.cast_names.op("@>")(func.jsonb_build_array(cast_name).cast(JSONB_TYPE))
            )
        if language is not None:
            filters.append(Movie.original_language == language)
        if min_runtime is not None:
            filters.append(Movie.runtime >= min_runtime)
        if max_runtime is not None:
            filters.append(Movie.runtime <= max_runtime)

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

    async def collection_completions(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        limit: int = 10,
    ) -> list[dict]:
        """Find directors/actors where user rated >= 3 films and return unrated ones."""
        rated_subq = select(Rating.movie_id).where(Rating.user_id == user_id)
        groups: list[dict] = []

        # --- Directors where user rated >= 3 films ---
        dir_stmt = (
            select(
                Movie.director,
                func.count().label("rated_count"),
                func.avg(Rating.rating).label("avg_rating"),
            )
            .join(Rating, (Rating.movie_id == Movie.id) & (Rating.user_id == user_id))
            .where(Movie.director.isnot(None))
            .group_by(Movie.director)
            .having(func.count() >= 3)
            .order_by(desc("avg_rating"))
        )
        dir_result = await db.execute(dir_stmt)
        for director_name, rated_count, avg_rating in dir_result.all():
            total_stmt = (
                select(func.count())
                .select_from(Movie)
                .where(func.lower(Movie.director) == func.lower(director_name))
            )
            total_result = await db.execute(total_stmt)
            total_by_creator = total_result.scalar_one()

            missing_stmt = (
                select(Movie)
                .where(func.lower(Movie.director) == func.lower(director_name))
                .where(Movie.id.notin_(rated_subq))
                .order_by(Movie.vote_average.desc())
            )
            missing_result = await db.execute(missing_stmt)
            missing_movies = list(missing_result.scalars().all())

            if missing_movies:
                groups.append(
                    {
                        "creator_type": "director",
                        "creator_name": director_name,
                        "rated_count": int(rated_count),
                        "avg_rating": round(float(avg_rating), 1),
                        "total_by_creator": total_by_creator,
                        "missing": missing_movies,
                    }
                )

        # --- Actors where user rated >= 3 films ---
        actor_name_col = func.jsonb_array_elements_text(Movie.cast_names).label("actor_name")
        actor_unnested = (
            select(actor_name_col, Movie.id.label("movie_id"), Rating.rating)
            .join(Rating, (Rating.movie_id == Movie.id) & (Rating.user_id == user_id))
            .where(Movie.cast_names != cast("[]", JSONB_TYPE))
            .subquery()
        )
        actor_stmt = (
            select(
                actor_unnested.c.actor_name,
                func.count(func.distinct(actor_unnested.c.movie_id)).label("rated_count"),
                func.avg(actor_unnested.c.rating).label("avg_rating"),
            )
            .group_by(actor_unnested.c.actor_name)
            .having(func.count(func.distinct(actor_unnested.c.movie_id)) >= 3)
            .order_by(desc("avg_rating"))
            .limit(20)
        )
        actor_result = await db.execute(actor_stmt)
        for actor_name_val, rated_count, avg_rating in actor_result.all():
            total_stmt = (
                select(func.count())
                .select_from(Movie)
                .where(
                    Movie.cast_names.op("@>")(
                        func.jsonb_build_array(actor_name_val).cast(JSONB_TYPE)
                    )
                )
            )
            total_result = await db.execute(total_stmt)
            total_by_creator = total_result.scalar_one()

            missing_stmt = (
                select(Movie)
                .where(
                    Movie.cast_names.op("@>")(
                        func.jsonb_build_array(actor_name_val).cast(JSONB_TYPE)
                    )
                )
                .where(Movie.id.notin_(rated_subq))
                .order_by(Movie.vote_average.desc())
            )
            missing_result = await db.execute(missing_stmt)
            missing_movies = list(missing_result.scalars().all())

            if missing_movies:
                groups.append(
                    {
                        "creator_type": "actor",
                        "creator_name": actor_name_val,
                        "rated_count": int(rated_count),
                        "avg_rating": round(float(avg_rating), 1),
                        "total_by_creator": total_by_creator,
                        "missing": missing_movies,
                    }
                )

        # Sort all groups by avg_rating descending
        groups.sort(key=lambda g: g["avg_rating"], reverse=True)

        # Limit total missing movies across all groups
        total_missing = 0
        trimmed: list[dict] = []
        for g in groups:
            remaining = limit - total_missing
            if remaining <= 0:
                break
            if len(g["missing"]) > remaining:
                g["missing"] = g["missing"][:remaining]
            total_missing += len(g["missing"])
            trimmed.append(g)

        return trimmed

    async def controversial(
        self,
        db: AsyncSession,
        *,
        min_ratings: int = 100,
        limit: int = 20,
    ) -> list[tuple[Movie, float, float, int, dict[int, int]]]:
        """Return movies with the highest rating standard deviation."""
        avg_col = func.avg(Rating.rating).label("avg_rating")
        stddev_col = func.stddev_samp(Rating.rating).label("stddev_rating")
        count_col = func.count(Rating.id).label("rating_count")

        stmt = (
            select(Rating.movie_id, avg_col, stddev_col, count_col)
            .group_by(Rating.movie_id)
            .having(func.count(Rating.id) >= min_ratings)
            .order_by(desc(stddev_col))
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return []

        ordered_ids = [row[0] for row in rows]
        stats = {row[0]: (float(row[1]), float(row[2]), int(row[3])) for row in rows}

        # Batch-fetch rating histograms
        hist_stmt = (
            select(Rating.movie_id, Rating.rating, func.count().label("cnt"))
            .where(Rating.movie_id.in_(ordered_ids))
            .group_by(Rating.movie_id, Rating.rating)
        )
        hist_result = await db.execute(hist_stmt)
        histograms: dict[int, dict[int, int]] = {
            mid: {r: 0 for r in range(1, 11)} for mid in ordered_ids
        }
        for mid, rating, cnt in hist_result.all():
            histograms[mid][rating] = int(cnt)

        movies_map = await self.get_movies_by_ids(ordered_ids, db)
        return [
            (movies_map[mid], *stats[mid], histograms[mid])
            for mid in ordered_ids
            if mid in movies_map
        ]

    async def genre_decade_counts(
        self,
        db: AsyncSession,
        *,
        min_count: int = 5,
    ) -> list[tuple[str, int, int]]:
        """Return (genre, decade, movie_count) for genre-decade combos with enough movies."""
        stmt = text(
            "SELECT genre, "
            "(FLOOR(EXTRACT(YEAR FROM release_date) / 10) * 10)::int AS decade, "
            "COUNT(*)::int AS cnt "
            "FROM movies, jsonb_array_elements_text(genres) AS genre "
            "WHERE release_date IS NOT NULL "
            "GROUP BY genre, decade "
            "HAVING COUNT(*) >= :min_count "
            "ORDER BY decade DESC, genre"
        )
        result = await db.execute(stmt, {"min_count": min_count})
        return [(row[0], int(row[1]), int(row[2])) for row in result.all()]

    async def top_by_genre_decade(
        self,
        db: AsyncSession,
        *,
        genre: str,
        decade: int,
        min_ratings: int = 10,
        limit: int = 20,
    ) -> list[tuple[Movie, float, int]]:
        """Top-rated movies in a genre within a specific decade."""
        year_min = decade
        year_max = decade + 9

        avg_rating_col = func.avg(Rating.rating).label("avg_rating")
        rating_count_col = func.count(Rating.id).label("rating_count")

        stmt = (
            select(Movie, avg_rating_col, rating_count_col)
            .join(Rating, Rating.movie_id == Movie.id)
            .where(
                Movie.genres.op("@>")(cast([genre], JSONB_TYPE)),
                extract("year", Movie.release_date) >= year_min,
                extract("year", Movie.release_date) <= year_max,
            )
            .group_by(Movie.id)
            .having(func.count(Rating.id) >= min_ratings)
            .order_by(desc(avg_rating_col))
            .limit(limit)
        )

        result = await db.execute(stmt)
        return [(row[0], float(row[1]), int(row[2])) for row in result.all()]

    async def top_by_year(
        self,
        db: AsyncSession,
        *,
        year: int,
        min_ratings: int = 10,
        limit: int = 20,
    ) -> list[tuple[Movie, float, int]]:
        """Top-rated movies for a specific year."""
        avg_rating_col = func.avg(Rating.rating).label("avg_rating")
        rating_count_col = func.count(Rating.id).label("rating_count")

        stmt = (
            select(Movie, avg_rating_col, rating_count_col)
            .join(Rating, Rating.movie_id == Movie.id)
            .where(extract("year", Movie.release_date) == year)
            .group_by(Movie.id)
            .having(func.count(Rating.id) >= min_ratings)
            .order_by(desc(avg_rating_col))
            .limit(limit)
        )

        result = await db.execute(stmt)
        return [(row[0], float(row[1]), int(row[2])) for row in result.all()]

    async def genre_decade_preview_posters(
        self,
        db: AsyncSession,
        *,
        genre: str,
        decade: int,
        limit: int = 4,
    ) -> list[str]:
        """Return up to N poster_paths for top movies in a genre-decade combo."""
        year_min = decade
        year_max = decade + 9

        stmt = (
            select(Movie.poster_path)
            .where(
                Movie.genres.op("@>")(cast([genre], JSONB_TYPE)),
                extract("year", Movie.release_date) >= year_min,
                extract("year", Movie.release_date) <= year_max,
                Movie.poster_path.isnot(None),
            )
            .order_by(desc(Movie.vote_average))
            .limit(limit)
        )

        result = await db.execute(stmt)
        return [row[0] for row in result.all()]

    async def find_direct_connections(
        self,
        movie_id1: int,
        movie_id2: int,
        db: AsyncSession,
    ) -> tuple[Movie | None, Movie | None, list[dict]]:
        """Find shared attributes between two movies."""
        movie1 = await self.get_by_id(movie_id1, db)
        movie2 = await self.get_by_id(movie_id2, db)
        if movie1 is None or movie2 is None:
            return movie1, movie2, []

        connections: list[dict] = []

        # Shared actors
        shared_actors = set(movie1.cast_names or []) & set(movie2.cast_names or [])
        for actor in sorted(shared_actors):
            connections.append(
                {"type": "actor", "value": actor, "details": "appears in both movies"}
            )

        # Same director
        if movie1.director and movie2.director and movie1.director == movie2.director:
            connections.append(
                {"type": "director", "value": movie1.director, "details": "directed both movies"}
            )

        # Shared genres
        shared_genres = set(movie1.genres or []) & set(movie2.genres or [])
        for genre in sorted(shared_genres):
            connections.append({"type": "genre", "value": genre, "details": "shared genre"})

        # Shared keywords
        shared_keywords = set(movie1.keywords or []) & set(movie2.keywords or [])
        for kw in sorted(shared_keywords):
            connections.append({"type": "keyword", "value": kw, "details": "shared keyword"})

        return movie1, movie2, connections

    async def _movies_by_person(
        self,
        person_name: str,
        db: AsyncSession,
        limit: int = 50,
    ) -> list[Movie]:
        """Find movies featuring a person as actor or director."""
        stmt = (
            select(Movie)
            .where(
                (Movie.cast_names.op("@>")(cast([person_name], JSONB_TYPE)))
                | (Movie.director == person_name)
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_shortest_path(
        self,
        movie_id1: int,
        movie_id2: int,
        db: AsyncSession,
        max_depth: int = 6,
    ) -> tuple[Movie | None, Movie | None, list[dict], bool]:
        """BFS shortest path between two movies through shared cast/directors."""
        movie1 = await self.get_by_id(movie_id1, db)
        movie2 = await self.get_by_id(movie_id2, db)
        if movie1 is None or movie2 is None:
            return movie1, movie2, [], False

        if movie1.id == movie2.id:
            return movie1, movie2, [{"movie": movie1, "linked_by": None}], True

        # Check direct connection first
        people1 = set(movie1.cast_names or [])
        if movie1.director:
            people1.add(movie1.director)
        people2 = set(movie2.cast_names or [])
        if movie2.director:
            people2.add(movie2.director)

        direct_link = people1 & people2
        if direct_link:
            person = sorted(direct_link)[0]
            return (
                movie1,
                movie2,
                [
                    {"movie": movie1, "linked_by": None},
                    {
                        "movie": movie2,
                        "linked_by": (
                            f"actor: {person}"
                            if person != movie1.director
                            else f"director: {person}"
                        ),
                    },
                ],
                True,
            )

        # BFS
        person_cache: dict[str, list[Movie]] = {}
        # visited: movie_id -> (parent_movie_id, linking_person)
        visited: dict[int, tuple[int | None, str | None]] = {movie1.id: (None, None)}
        frontier: list[Movie] = [movie1]
        target_id = movie2.id

        for _depth in range(max_depth):
            next_frontier: list[Movie] = []
            for movie in frontier:
                people = list(movie.cast_names or [])
                if movie.director:
                    people.append(movie.director)

                for person in people:
                    if person not in person_cache:
                        person_cache[person] = await self._movies_by_person(person, db)

                    for neighbor in person_cache[person]:
                        if neighbor.id in visited:
                            continue
                        visited[neighbor.id] = (movie.id, person)
                        if neighbor.id == target_id:
                            # Reconstruct path
                            path: list[dict] = []
                            current_id: int | None = target_id
                            movie_map = {
                                m.id: m for movies in person_cache.values() for m in movies
                            }
                            movie_map[movie1.id] = movie1
                            movie_map[movie2.id] = movie2
                            while current_id is not None:
                                parent_id, link_person = visited[current_id]
                                label = f"actor: {link_person}" if link_person else None
                                path.append({"movie": movie_map[current_id], "linked_by": label})
                                current_id = parent_id
                            path.reverse()
                            return movie1, movie2, path, True
                        next_frontier.append(neighbor)
            frontier = next_frontier
            if not frontier:
                break

        return movie1, movie2, [], False

    async def get_movie_dna(
        self,
        movie_id: int,
        db: AsyncSession,
        content_recommender: ContentRecommender,
    ) -> dict | None:
        """Compute a movie's DNA: genre weights, keyword weights, decade, and mood tags."""
        from collections import Counter

        movie = await self.get_by_id(movie_id, db)
        if movie is None:
            return None

        # Decade from release date
        decade = None
        if movie.release_date is not None:
            decade = movie.release_date.year // 10 * 10

        # Find 10 nearest neighbors via content recommender
        similar_pairs = await content_recommender.get_similar_movies(movie_id, db, top_k=10)
        neighbor_ids = [mid for mid, _ in similar_pairs]
        neighbors_map = await self.get_movies_by_ids(neighbor_ids, db)
        neighbors = [neighbors_map[mid] for mid in neighbor_ids if mid in neighbors_map]

        # Genre weights: frequency across movie + neighbors, normalized
        all_movies = [movie, *neighbors]
        genre_counter: Counter[str] = Counter()
        for m in all_movies:
            for g in m.genres or []:
                genre_counter[g] += 1
        total_movies = len(all_movies)
        genre_weights = [
            {"genre": g, "weight": round(count / total_movies, 2)}
            for g, count in genre_counter.most_common()
        ]

        # Keyword weights: frequency across movie + neighbors, top 10
        keyword_counter: Counter[str] = Counter()
        for m in all_movies:
            for kw in m.keywords or []:
                keyword_counter[kw] += 1
        max_kw_count = keyword_counter.most_common(1)[0][1] if keyword_counter else 1
        top_keywords = [
            {"keyword": kw, "weight": round(count / max_kw_count, 2)}
            for kw, count in keyword_counter.most_common(10)
        ]

        # Mood tags: keywords in >=2 neighbors but NOT in this movie
        movie_keywords = set(movie.keywords or [])
        neighbor_kw_counter: Counter[str] = Counter()
        for n in neighbors:
            for kw in n.keywords or []:
                if kw not in movie_keywords:
                    neighbor_kw_counter[kw] += 1
        mood_tags = [kw for kw, count in neighbor_kw_counter.most_common(5) if count >= 2]

        return {
            "movie_id": movie.id,
            "title": movie.title,
            "genres": genre_weights,
            "top_keywords": top_keywords,
            "decade": decade,
            "mood_tags": mood_tags,
            "director": movie.director,
            "vote_average": movie.vote_average,
        }

    async def embedding_cosine_similarity(
        self,
        movie_id1: int,
        movie_id2: int,
        db: AsyncSession,
    ) -> float | None:
        """Compute cosine similarity between two movies' stored embeddings."""
        result = await db.execute(
            text(
                "SELECT 1 - (m1.embedding <=> m2.embedding) AS cosine_sim "
                "FROM movies m1, movies m2 "
                "WHERE m1.id = :id1 AND m2.id = :id2 "
                "AND m1.embedding IS NOT NULL AND m2.embedding IS NOT NULL"
            ),
            {"id1": movie_id1, "id2": movie_id2},
        )
        row = result.first()
        return round(float(row[0]), 4) if row else None
