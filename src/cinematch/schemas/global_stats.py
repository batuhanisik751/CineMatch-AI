"""Pydantic schemas for global platform statistics."""

from __future__ import annotations

from pydantic import BaseModel


class GlobalStatsMovieRef(BaseModel):
    """Lightweight movie reference used in global stats."""

    id: int
    title: str
    poster_path: str | None
    vote_average: float
    genres: list[str]
    release_date: str | None
    rating_count: int
    avg_user_rating: float | None = None


class GlobalStatsUserRef(BaseModel):
    """Lightweight user reference used in global stats."""

    id: int
    movielens_id: int
    rating_count: int


class GlobalStatsResponse(BaseModel):
    """Platform-wide statistics."""

    total_movies: int
    total_users: int
    total_ratings: int
    avg_rating: float
    most_rated_movie: GlobalStatsMovieRef | None
    highest_rated_movie: GlobalStatsMovieRef | None
    most_active_user: GlobalStatsUserRef | None
    ratings_this_week: int
