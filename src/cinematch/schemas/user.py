"""Pydantic schemas for user endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from cinematch.schemas.movie import MovieSummary


class UserResponse(BaseModel):
    """User details."""

    id: int
    movielens_id: int | None = None
    email: str | None = None
    username: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenreCount(BaseModel):
    """Genre with rating count and percentage."""

    genre: str
    count: int
    percentage: float


class RatingBucket(BaseModel):
    """Rating value bucket with count."""

    rating: str
    count: int


class PersonCount(BaseModel):
    """Person (director/actor) with count of rated movies."""

    name: str
    count: int


class MonthlyActivity(BaseModel):
    """Monthly rating activity bucket."""

    month: str
    count: int


class UserStatsResponse(BaseModel):
    """Aggregated user profile analytics."""

    user_id: int
    total_ratings: int
    average_rating: float
    genre_distribution: list[GenreCount]
    rating_distribution: list[RatingBucket]
    top_directors: list[PersonCount]
    top_actors: list[PersonCount]
    rating_timeline: list[MonthlyActivity]


class SurpriseResponse(BaseModel):
    """Response for surprise/serendipity recommendations."""

    user_id: int
    excluded_genres: list[str]
    results: list[MovieSummary]
    limit: int


class CollectionGroup(BaseModel):
    """A creator (director/actor) with their unrated films."""

    creator_type: str
    creator_name: str
    rated_count: int
    avg_rating: float
    total_by_creator: int
    missing: list[MovieSummary]


class CompletionsResponse(BaseModel):
    """Response for collection completion suggestions."""

    user_id: int
    groups: list[CollectionGroup]
    total_missing: int


class DirectorGapsResponse(BaseModel):
    """Top directors the user loves, with unseen films."""

    user_id: int
    groups: list[CollectionGroup]
    total_missing: int


class ActorGapsResponse(BaseModel):
    """Top actors the user loves, with unseen films."""

    user_id: int
    groups: list[CollectionGroup]
    total_missing: int


class FeedSection(BaseModel):
    """One carousel section in the personalized feed."""

    key: str
    title: str
    movies: list[MovieSummary]


class FeedResponse(BaseModel):
    """Full personalized home feed."""

    user_id: int
    is_personalized: bool
    sections: list[FeedSection]


class RatedFilm(BaseModel):
    """A film the user has rated, used in affinity detail."""

    movie_id: int
    title: str
    rating: int
    poster_path: str | None


class AffinityEntry(BaseModel):
    """A director or actor ranked by affinity score."""

    name: str
    role: str
    avg_rating: float
    count: int
    weighted_score: float
    films_rated: list[RatedFilm]


class AffinitiesResponse(BaseModel):
    """Director and actor affinity rankings for a user."""

    user_id: int
    directors: list[AffinityEntry]
    actors: list[AffinityEntry]
