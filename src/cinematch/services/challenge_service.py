"""Weekly rating challenge generation and progress tracking."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_TARGET = 5


def _week_key(d: date | None = None) -> tuple[int, int, str]:
    """Return (iso_year, iso_week, label) for the given date."""
    d = d or date.today()
    iso_year, iso_week, _ = d.isocalendar()
    return iso_year, iso_week, f"{iso_year}-W{iso_week:02d}"


def _week_seed(year: int, week: int) -> int:
    h = hashlib.sha256(f"challenges:{year}:W{week}".encode()).hexdigest()
    return int(h[:8], 16)


def _week_boundaries(year: int, week: int) -> tuple[datetime, datetime]:
    """Return (monday_00:00_utc, next_monday_00:00_utc) for an ISO week."""
    monday = datetime.fromisocalendar(year, week, 1).replace(tzinfo=UTC)
    next_monday = monday + timedelta(days=7)
    return monday, next_monday


class ChallengeService:
    """Generates deterministic weekly challenges and tracks progress."""

    async def _get_parameter_pools(
        self, db: AsyncSession
    ) -> tuple[list[str], list[int], list[tuple[str, int]]]:
        """Fetch sorted pools of genres, decades, and directors from the DB."""
        genre_result = await db.execute(
            text(
                "SELECT DISTINCT genre FROM movies, "
                "jsonb_array_elements_text(movies.genres) AS genre "
                "ORDER BY genre"
            )
        )
        genres = [r[0] for r in genre_result.all()]

        decade_result = await db.execute(
            text(
                "SELECT DISTINCT (EXTRACT(DECADE FROM release_date)::int * 10) AS decade "
                "FROM movies WHERE release_date IS NOT NULL "
                "ORDER BY decade"
            )
        )
        decades = [r[0] for r in decade_result.all()]

        director_result = await db.execute(
            text(
                "SELECT director, COUNT(*)::int AS cnt "
                "FROM movies WHERE director IS NOT NULL "
                "GROUP BY director HAVING COUNT(*) >= :target "
                "ORDER BY director"
            ),
            {"target": _TARGET},
        )
        directors = [(r[0], r[1]) for r in director_result.all()]

        return genres, decades, directors

    async def get_current_challenges(
        self, db: AsyncSession, *, today: date | None = None
    ) -> dict[str, Any]:
        """Return this week's three challenges (deterministic)."""
        year, week, week_label = _week_key(today)
        seed = _week_seed(year, week)
        rng = random.Random(seed)

        genres, decades, directors = await self._get_parameter_pools(db)

        challenges: list[dict[str, Any]] = []

        if genres:
            genre = genres[rng.randrange(len(genres))]
            challenges.append(
                {
                    "id": f"genre_{genre.lower().replace(' ', '_')}_{year}w{week:02d}",
                    "template": "genre",
                    "title": f"Rate {_TARGET} {genre} movies",
                    "description": f"Explore the {genre} genre this week",
                    "icon": "movie_filter",
                    "target": _TARGET,
                    "parameter": genre,
                }
            )

        if decades:
            decade = decades[rng.randrange(len(decades))]
            challenges.append(
                {
                    "id": f"decade_{decade}s_{year}w{week:02d}",
                    "template": "decade",
                    "title": f"Explore the {decade}s",
                    "description": f"Travel back to the {decade}s and rate {_TARGET} films",
                    "icon": "history",
                    "target": _TARGET,
                    "parameter": f"{decade}s",
                }
            )

        if directors:
            director_name, _ = directors[rng.randrange(len(directors))]
            challenges.append(
                {
                    "id": f"director_{director_name.lower().replace(' ', '_')}_{year}w{week:02d}",
                    "template": "director",
                    "title": f"Director deep-dive: {director_name}",
                    "description": f"Watch and rate {_TARGET} films by {director_name}",
                    "icon": "person",
                    "target": _TARGET,
                    "parameter": director_name,
                }
            )

        return {"week": week_label, "challenges": challenges}

    async def get_user_progress(
        self, user_id: int, db: AsyncSession, *, today: date | None = None
    ) -> dict[str, Any]:
        """Return challenges with user-specific progress for the current week."""
        current = await self.get_current_challenges(db, today=today)
        year, week, _ = _week_key(today)
        week_start, week_end = _week_boundaries(year, week)

        progress_challenges: list[dict[str, Any]] = []

        for challenge in current["challenges"]:
            template = challenge["template"]
            param = challenge["parameter"]

            if template == "genre":
                # Strip trailing "s" if present — parameter is the raw genre name
                result = await db.execute(
                    text(
                        "SELECT r.movie_id FROM ratings r "
                        "JOIN movies m ON r.movie_id = m.id "
                        "WHERE r.user_id = :uid "
                        "AND r.timestamp >= :ws AND r.timestamp < :we "
                        "AND m.genres @> CAST(:genre_json AS jsonb)"
                    ),
                    {
                        "uid": user_id,
                        "ws": week_start,
                        "we": week_end,
                        "genre_json": json.dumps([param]),
                    },
                )
            elif template == "decade":
                # parameter is like "1990s" — extract the int
                decade_int = int(param.rstrip("s"))
                result = await db.execute(
                    text(
                        "SELECT r.movie_id FROM ratings r "
                        "JOIN movies m ON r.movie_id = m.id "
                        "WHERE r.user_id = :uid "
                        "AND r.timestamp >= :ws AND r.timestamp < :we "
                        "AND m.release_date IS NOT NULL "
                        "AND EXTRACT(DECADE FROM m.release_date)::int * 10 = :decade"
                    ),
                    {
                        "uid": user_id,
                        "ws": week_start,
                        "we": week_end,
                        "decade": decade_int,
                    },
                )
            elif template == "director":
                result = await db.execute(
                    text(
                        "SELECT r.movie_id FROM ratings r "
                        "JOIN movies m ON r.movie_id = m.id "
                        "WHERE r.user_id = :uid "
                        "AND r.timestamp >= :ws AND r.timestamp < :we "
                        "AND m.director = :director"
                    ),
                    {
                        "uid": user_id,
                        "ws": week_start,
                        "we": week_end,
                        "director": param,
                    },
                )
            else:
                result = None

            qualifying_ids = [r[0] for r in result.all()] if result else []
            progress = len(qualifying_ids)

            progress_challenges.append(
                {
                    **challenge,
                    "progress": progress,
                    "completed": progress >= challenge["target"],
                    "qualifying_movie_ids": qualifying_ids,
                }
            )

        completed_count = sum(1 for c in progress_challenges if c["completed"])
        return {
            "user_id": user_id,
            "week": current["week"],
            "challenges": progress_challenges,
            "completed_count": completed_count,
            "total_count": len(progress_challenges),
        }
