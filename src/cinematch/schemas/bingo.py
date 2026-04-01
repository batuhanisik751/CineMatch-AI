"""Pydantic schemas for Movie Bingo cards."""

from __future__ import annotations

from pydantic import BaseModel


class BingoCell(BaseModel):
    """A single cell on the 5x5 bingo card."""

    index: int
    template: str
    label: str
    parameter: str | None = None
    completed: bool
    movie_id: int | None = None


class BingoCardResponse(BaseModel):
    """Response for GET /users/{id}/bingo."""

    user_id: int
    seed: str
    cells: list[BingoCell]
    completed_lines: list[list[int]]
    total_completed: int
    bingo_count: int
