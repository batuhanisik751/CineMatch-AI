"""Pydantic schemas for rewatch recommendations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from cinematch.schemas.movie import MovieSummary


class RewatchItem(BaseModel):
    """A single rewatch suggestion."""

    movie: MovieSummary
    user_rating: int
    rated_at: datetime
    days_since_rated: int
    is_classic: bool

    model_config = ConfigDict(from_attributes=True)


class RewatchResponse(BaseModel):
    """Response for the rewatch endpoint."""

    user_id: int
    suggestions: list[RewatchItem]
    total: int
