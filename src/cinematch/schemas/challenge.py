"""Pydantic schemas for weekly rating challenges."""

from __future__ import annotations

from pydantic import BaseModel


class Challenge(BaseModel):
    """A single weekly challenge definition."""

    id: str
    template: str
    title: str
    description: str
    icon: str
    target: int
    parameter: str


class ChallengeWithProgress(Challenge):
    """Challenge with user-specific progress tracking."""

    progress: int
    completed: bool
    qualifying_movie_ids: list[int]


class ChallengesCurrentResponse(BaseModel):
    """Response for GET /challenges/current."""

    week: str
    challenges: list[Challenge]


class ChallengesProgressResponse(BaseModel):
    """Response for GET /users/{id}/challenges/progress."""

    user_id: int
    week: str
    challenges: list[ChallengeWithProgress]
    completed_count: int
    total_count: int
