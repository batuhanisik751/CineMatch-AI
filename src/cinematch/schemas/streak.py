"""Pydantic schemas for rating streaks and milestones."""

from __future__ import annotations

from pydantic import BaseModel


class Milestone(BaseModel):
    threshold: int
    reached: bool
    label: str


class StreakResponse(BaseModel):
    user_id: int
    current_streak: int
    longest_streak: int
    total_ratings: int
    milestones: list[Milestone]
