"""Service for detecting a user's cinematic blind spots."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BlindSpotService:
    """Surface popular, highly-regarded movies the user has never rated."""

    async def get_blind_spots(
        self,
        user_id: int,
        db: AsyncSession,
        *,
        limit: int = 20,
        genre: str | None = None,
    ) -> dict[str, Any]:
        """Return blind spot movies matching BlindSpotResponse schema."""

        if genre is not None:
            query = text("""
                SELECT
                    m.id,
                    m.title,
                    m.genres,
                    m.vote_average,
                    m.vote_count,
                    m.release_date,
                    m.poster_path,
                    m.original_language,
                    m.runtime,
                    (m.vote_count * m.vote_average) AS popularity_score
                FROM movies m
                WHERE m.id NOT IN (
                    SELECT r.movie_id FROM ratings r WHERE r.user_id = :uid
                )
                AND m.genres @> :genre_filter::jsonb
                ORDER BY (m.vote_count * m.vote_average) DESC
                LIMIT :lim
            """)
            params: dict[str, Any] = {
                "uid": user_id,
                "lim": limit,
                "genre_filter": json.dumps([genre]),
            }
        else:
            query = text("""
                SELECT
                    m.id,
                    m.title,
                    m.genres,
                    m.vote_average,
                    m.vote_count,
                    m.release_date,
                    m.poster_path,
                    m.original_language,
                    m.runtime,
                    (m.vote_count * m.vote_average) AS popularity_score
                FROM movies m
                WHERE m.id NOT IN (
                    SELECT r.movie_id FROM ratings r WHERE r.user_id = :uid
                )
                ORDER BY (m.vote_count * m.vote_average) DESC
                LIMIT :lim
            """)
            params = {
                "uid": user_id,
                "lim": limit,
            }

        result = await db.execute(query, params)
        rows = result.all()

        movies = []
        for row in rows:
            movies.append(
                {
                    "movie": {
                        "id": row.id,
                        "title": row.title,
                        "genres": row.genres or [],
                        "vote_average": row.vote_average,
                        "release_date": row.release_date,
                        "poster_path": row.poster_path,
                        "original_language": row.original_language,
                        "runtime": row.runtime,
                    },
                    "vote_count": row.vote_count,
                    "popularity_score": float(row.popularity_score),
                }
            )

        return {
            "user_id": user_id,
            "genre": genre,
            "movies": movies,
            "total": len(movies),
        }
