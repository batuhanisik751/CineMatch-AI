"""Pydantic schemas for thematic collection endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from cinematch.schemas.movie import MovieSummary


class ThematicCollectionSummary(BaseModel):
    """Summary of a single thematic collection."""

    id: str
    title: str
    collection_type: str
    movie_count: int
    preview_posters: list[str] = []


class ThematicCollectionsResponse(BaseModel):
    """Response for listing available thematic collections."""

    results: list[ThematicCollectionSummary]
    collection_type: str | None


class ThematicCollectionMovieResult(BaseModel):
    """A movie within a thematic collection with rating stats."""

    movie: MovieSummary
    avg_rating: float
    rating_count: int


class ThematicCollectionDetailResponse(BaseModel):
    """Response for a single thematic collection's movies."""

    id: str
    title: str
    collection_type: str
    results: list[ThematicCollectionMovieResult]
    total: int
    limit: int
