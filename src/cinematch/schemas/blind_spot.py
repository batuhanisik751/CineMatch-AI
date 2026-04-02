"""Pydantic schemas for blind spot detection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cinematch.schemas.movie import MovieSummary


class BlindSpotItem(BaseModel):
    """A single blind spot movie."""

    movie: MovieSummary
    vote_count: int
    popularity_score: float

    model_config = ConfigDict(from_attributes=True)


class BlindSpotResponse(BaseModel):
    """Response for the blind spots endpoint."""

    user_id: int
    genre: str | None
    movies: list[BlindSpotItem]
    total: int
