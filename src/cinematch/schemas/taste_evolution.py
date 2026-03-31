"""Pydantic schemas for taste evolution timeline."""

from __future__ import annotations

from pydantic import BaseModel


class TasteEvolutionPeriod(BaseModel):
    period: str
    genres: dict[str, float]


class TasteEvolutionResponse(BaseModel):
    user_id: int
    granularity: str
    periods: list[TasteEvolutionPeriod]
