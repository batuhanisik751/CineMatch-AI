"""Personalized home feed service."""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

from sqlalchemy import select

from cinematch.models.rating import Rating
from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.user import FeedResponse, FeedSection

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.collab_recommender import CollabRecommender
    from cinematch.services.content_recommender import ContentRecommender
    from cinematch.services.dismissal_service import DismissalService
    from cinematch.services.hybrid_recommender import HybridRecommender
    from cinematch.services.movie_service import MovieService
    from cinematch.services.user_stats_service import UserStatsService

logger = logging.getLogger(__name__)


class FeedService:
    """Orchestrates existing services to build a personalized home feed."""

    def __init__(
        self,
        movie_service: MovieService,
        user_stats_service: UserStatsService,
        content_recommender: ContentRecommender | None,
        collab_recommender: CollabRecommender | None,
        hybrid_recommender: HybridRecommender | None,
        dismissal_service: DismissalService | None = None,
    ) -> None:
        self._movies = movie_service
        self._stats = user_stats_service
        self._content = content_recommender
        self._collab = collab_recommender
        self._hybrid = hybrid_recommender
        self._dismissal_service = dismissal_service

    async def generate_feed(
        self,
        user_id: int,
        db: AsyncSession,
        sections: int = 5,
    ) -> FeedResponse:
        """Build the personalized feed for a user."""
        stats = await self._stats.get_user_stats(user_id, db)

        if stats["total_ratings"] == 0:
            return await self._cold_start_feed(user_id, db)

        # Fetch rated IDs once for all sections
        result = await db.execute(select(Rating.movie_id).where(Rating.user_id == user_id))
        rated_ids = {row[0] for row in result.all()}

        # Also exclude dismissed movies
        if self._dismissal_service is not None:
            dismissed_ids = await self._dismissal_service.get_dismissed_movie_ids(user_id, db)
            rated_ids = rated_ids | dismissed_ids

        # Build sections in order, skip on failure
        builders = [
            self._section_because_you_rated,
            self._section_trending_for_you,
            self._section_hidden_gems,
            self._section_something_different,
            self._section_new_in_decade,
        ]

        built: list[FeedSection] = []
        for builder in builders[:sections]:
            try:
                section = await builder(user_id, db, rated_ids, stats)
                if section is not None and len(section.movies) > 0:
                    built.append(section)
            except Exception:
                logger.exception("Feed section %s failed", builder.__name__)

        return FeedResponse(
            user_id=user_id,
            is_personalized=True,
            sections=built,
        )

    # ------------------------------------------------------------------
    # Cold-start fallback
    # ------------------------------------------------------------------

    async def _cold_start_feed(self, user_id: int, db: AsyncSession) -> FeedResponse:
        """Generic feed for users with no ratings."""
        built: list[FeedSection] = []

        # Trending
        try:
            trending = await self._movies.trending(db, window=7, limit=10)
            if trending:
                built.append(
                    FeedSection(
                        key="trending",
                        title="Trending Now",
                        movies=[MovieSummary.model_validate(m) for m, _ in trending],
                    )
                )
        except Exception:
            logger.exception("Cold-start trending section failed")

        # Top Rated
        try:
            top_movies, _ = await self._movies.list_movies(db, sort_by="vote_average", limit=10)
            if top_movies:
                built.append(
                    FeedSection(
                        key="top_rated",
                        title="Top Rated",
                        movies=[MovieSummary.model_validate(m) for m in top_movies],
                    )
                )
        except Exception:
            logger.exception("Cold-start top-rated section failed")

        # Hidden Gems
        try:
            gems = await self._movies.hidden_gems(db, limit=10)
            if gems:
                built.append(
                    FeedSection(
                        key="hidden_gems",
                        title="Hidden Gems",
                        movies=[MovieSummary.model_validate(m) for m in gems],
                    )
                )
        except Exception:
            logger.exception("Cold-start hidden-gems section failed")

        return FeedResponse(
            user_id=user_id,
            is_personalized=False,
            sections=built,
        )

    # ------------------------------------------------------------------
    # Personalized section builders
    # ------------------------------------------------------------------

    async def _section_because_you_rated(
        self,
        user_id: int,
        db: AsyncSession,
        rated_ids: set[int],
        stats: dict,
    ) -> FeedSection | None:
        """Content-based recs from the user's highest-rated movie."""
        if self._hybrid is None or self._content is None:
            return None

        top_rated = await self._hybrid._get_user_top_rated_diverse(user_id, db, limit=5)
        if not top_rated:
            return None

        seed_id, _ = top_rated[0]
        seed_movie = await self._movies.get_by_id(seed_id, db)
        if seed_movie is None:
            return None

        similar = await self._content.get_similar_movies(seed_id, db, top_k=20)
        movie_ids = [mid for mid, _ in similar if mid not in rated_ids][:10]
        if not movie_ids:
            return None

        movies_map = await self._movies.get_movies_by_ids(movie_ids, db)
        movies = [
            MovieSummary.model_validate(movies_map[mid]) for mid in movie_ids if mid in movies_map
        ]

        return FeedSection(
            key="because_you_rated",
            title=f"Because you rated {seed_movie.title} highly",
            movies=movies,
        )

    async def _section_trending_for_you(
        self,
        user_id: int,
        db: AsyncSession,
        rated_ids: set[int],
        stats: dict,
    ) -> FeedSection | None:
        """ALS recommendations intersected with trending movies."""
        if self._collab is None:
            return None

        # Support both sync (full mode) and async (lightweight mode) collab
        import inspect

        sig = inspect.signature(self._collab.is_known_user)
        if "db" in sig.parameters:
            is_known = await self._collab.is_known_user(user_id, db)
        else:
            is_known = self._collab.is_known_user(user_id)
        if not is_known:
            return None

        sig_rec = inspect.signature(self._collab.recommend_for_user)
        if "db" in sig_rec.parameters:
            collab_results = await self._collab.recommend_for_user(
                user_id, db, top_k=50
            )
        else:
            collab_results = self._collab.recommend_for_user(user_id, top_k=50)
        if not collab_results:
            return None

        trending = await self._movies.trending(db, window=30, limit=50)
        trending_ids = {m.id for m, _ in trending}

        # Intersect: collab recs that are also trending, exclude rated
        intersection = [
            (mid, score)
            for mid, score in collab_results
            if mid in trending_ids and mid not in rated_ids
        ]
        intersection.sort(key=lambda x: x[1], reverse=True)

        # If intersection is small, pad with top collab results not yet rated
        if len(intersection) < 5:
            for mid, score in collab_results:
                if mid not in rated_ids and mid not in {m for m, _ in intersection}:
                    intersection.append((mid, score))
                if len(intersection) >= 10:
                    break

        movie_ids = [mid for mid, _ in intersection[:10]]
        if not movie_ids:
            return None

        movies_map = await self._movies.get_movies_by_ids(movie_ids, db)
        movies = [
            MovieSummary.model_validate(movies_map[mid]) for mid in movie_ids if mid in movies_map
        ]

        return FeedSection(
            key="trending_for_you",
            title="Trending with users like you",
            movies=movies,
        )

    async def _section_hidden_gems(
        self,
        user_id: int,
        db: AsyncSession,
        rated_ids: set[int],
        stats: dict,
    ) -> FeedSection | None:
        """Hidden gems in the user's top genre."""
        genre_dist = stats.get("genre_distribution", [])
        if not genre_dist:
            return None

        top_genre = genre_dist[0]["genre"]
        gems = await self._movies.hidden_gems(db, genre=top_genre, limit=20)

        filtered = [m for m in gems if m.id not in rated_ids][:10]
        if not filtered:
            return None

        return FeedSection(
            key="hidden_gems",
            title=f"Hidden gems in {top_genre}",
            movies=[MovieSummary.model_validate(m) for m in filtered],
        )

    async def _section_something_different(
        self,
        user_id: int,
        db: AsyncSession,
        rated_ids: set[int],
        stats: dict,
    ) -> FeedSection | None:
        """Serendipity picks outside the user's usual genres."""
        genre_dist = stats.get("genre_distribution", [])
        excluded_genres = [g["genre"] for g in genre_dist[:2]]

        movies = await self._movies.surprise_movies(
            db,
            excluded_genres=excluded_genres,
            excluded_movie_ids=list(rated_ids),
            limit=10,
        )
        if not movies:
            return None

        return FeedSection(
            key="something_different",
            title="Something different",
            movies=[MovieSummary.model_validate(m) for m in movies],
        )

    async def _section_new_in_decade(
        self,
        user_id: int,
        db: AsyncSession,
        rated_ids: set[int],
        stats: dict,
    ) -> FeedSection | None:
        """Popular unrated movies from the user's favorite decade."""
        if not rated_ids:
            return None

        # Determine favorite decade from rated movies
        movies_map = await self._movies.get_movies_by_ids(list(rated_ids), db)
        decades = [
            (m.release_date.year // 10) * 10
            for m in movies_map.values()
            if m.release_date is not None
        ]
        if not decades:
            return None

        fav_decade = Counter(decades).most_common(1)[0][0]

        decade_results, _ = await self._movies.top_by_decade(
            db, decade=fav_decade, min_ratings=5, limit=20
        )

        filtered = [m for m, _, _ in decade_results if m.id not in rated_ids][:10]
        if not filtered:
            return None

        return FeedSection(
            key="new_in_decade",
            title=f"New to you in the {fav_decade}s",
            movies=[MovieSummary.model_validate(m) for m in filtered],
        )
