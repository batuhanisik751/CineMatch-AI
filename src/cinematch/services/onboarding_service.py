"""Onboarding service — selects genre-diverse popular movies for new users."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from sqlalchemy import func, select, text

from cinematch.models.movie import Movie
from cinematch.models.rating import Rating

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class OnboardingService:
    """Select popular, genre-diverse movies for onboarding and check status."""

    async def get_onboarding_movies(
        self,
        user_id: int,
        count: int,
        db: AsyncSession,
    ) -> list[Movie]:
        """Return *count* popular movies spread across genres.

        Algorithm:
        1. Pick the top movie (by vote_count) per primary genre,
           excluding movies the user already rated.
        2. If fewer genres than *count*, fill remaining slots from
           the overall top vote_count movies (excluding selected + rated).
        3. Shuffle to avoid predictable genre ordering.
        """
        # Subquery: movie IDs already rated by this user
        rated_subq = (
            select(Rating.movie_id)
            .where(Rating.user_id == user_id)
            .correlate(None)
            .scalar_subquery()
        )

        # CTE: rank movies within each primary genre by vote_count
        primary_genre = Movie.genres[0].astext.label("primary_genre")
        row_num = (
            func.row_number()
            .over(partition_by=primary_genre, order_by=Movie.vote_count.desc())
            .label("rn")
        )

        ranked_cte = (
            select(Movie.id, primary_genre, row_num)
            .where(
                Movie.vote_count > 0,
                func.jsonb_array_length(Movie.genres) > 0,
                Movie.id.notin_(rated_subq),
            )
            .cte("ranked")
        )

        # Step 1: one movie per genre (top by vote_count)
        per_genre_ids_q = (
            select(ranked_cte.c.id)
            .where(ranked_cte.c.rn == 1)
            .order_by(text("random()"))
            .limit(count)
        )
        per_genre_result = await db.execute(per_genre_ids_q)
        selected_ids: list[int] = list(per_genre_result.scalars().all())

        # Step 2: fill remaining slots from overall top vote_count
        remaining = count - len(selected_ids)
        if remaining > 0:
            fill_q = (
                select(Movie.id)
                .where(
                    Movie.vote_count > 0,
                    func.jsonb_array_length(Movie.genres) > 0,
                    Movie.id.notin_(rated_subq),
                    Movie.id.notin_(selected_ids) if selected_ids else True,
                )
                .order_by(Movie.vote_count.desc())
                .limit(remaining)
            )
            fill_result = await db.execute(fill_q)
            selected_ids.extend(fill_result.scalars().all())

        if not selected_ids:
            return []

        # Fetch full Movie objects
        movies_q = select(Movie).where(Movie.id.in_(selected_ids))
        movies_result = await db.execute(movies_q)
        movies = list(movies_result.scalars().all())

        random.shuffle(movies)
        return movies

    async def get_onboarding_status(
        self,
        user_id: int,
        threshold: int,
        db: AsyncSession,
    ) -> dict:
        """Return onboarding completion status based on rating count."""
        count_q = select(func.count()).select_from(Rating).where(Rating.user_id == user_id)
        result = await db.execute(count_q)
        rating_count = result.scalar_one()

        return {
            "user_id": user_id,
            "completed": rating_count >= threshold,
            "rating_count": rating_count,
            "threshold": threshold,
        }
