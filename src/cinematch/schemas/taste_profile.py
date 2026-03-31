"""Pydantic schemas for taste profile endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class TasteInsight(BaseModel):
    """A single taste profile insight."""

    key: str
    icon: str
    text: str


class TasteProfileResponse(BaseModel):
    """Full taste profile summary for a user."""

    user_id: int
    total_ratings: int
    insights: list[TasteInsight]
    llm_summary: str | None = None
