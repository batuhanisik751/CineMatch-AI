"""Movie Bingo card generation and progress tracking."""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 5x5 grid, center cell (index 12) is FREE
_GRID_SIZE = 25
_FREE_INDEX = 12

# All possible bingo lines: 5 rows + 5 cols + 2 diagonals = 12 lines
_LINES: list[list[int]] = []
for r in range(5):
    _LINES.append([r * 5 + c for c in range(5)])  # rows
for c in range(5):
    _LINES.append([r * 5 + c for r in range(5)])  # cols
_LINES.append([i * 6 for i in range(5)])  # top-left to bottom-right
_LINES.append([4 + i * 4 for i in range(5)])  # top-right to bottom-left


def _month_seed(seed_str: str) -> int:
    h = hashlib.sha256(f"bingo:{seed_str}".encode()).hexdigest()
    return int(h[:8], 16)


class BingoService:
    """Generates deterministic monthly bingo cards and tracks progress."""

    async def _get_parameter_pools(self, db: AsyncSession) -> dict[str, list[Any]]:
        """Fetch sorted pools of genres, decades, directors, and keywords."""
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
                "SELECT director FROM movies "
                "WHERE director IS NOT NULL "
                "GROUP BY director HAVING COUNT(*) >= 3 "
                "ORDER BY director"
            )
        )
        directors = [r[0] for r in director_result.all()]

        keyword_result = await db.execute(
            text(
                "SELECT kw FROM movies, "
                "jsonb_array_elements_text(movies.keywords) AS kw "
                "GROUP BY kw HAVING COUNT(*) >= 5 "
                "ORDER BY kw"
            )
        )
        keywords = [r[0] for r in keyword_result.all()]

        return {
            "genres": genres,
            "decades": decades,
            "directors": directors,
            "keywords": keywords,
        }

    def _build_cells(self, rng: random.Random, pools: dict[str, list[Any]]) -> list[dict[str, Any]]:
        """Build 25 bingo cells (24 categories + 1 FREE)."""
        templates: list[dict[str, Any]] = []
        used: set[str] = set()

        def _add(template: str, label: str, parameter: str | None = None) -> bool:
            key = f"{template}:{parameter}"
            if key in used:
                return False
            used.add(key)
            templates.append({"template": template, "label": label, "parameter": parameter})
            return True

        # Build a pool of candidates for each template type
        genre_pool = list(pools["genres"])
        decade_pool = list(pools["decades"])
        director_pool = list(pools["directors"])
        keyword_pool = list(pools["keywords"])

        rng.shuffle(genre_pool)
        rng.shuffle(decade_pool)
        rng.shuffle(director_pool)
        rng.shuffle(keyword_pool)

        # Fill cells: ~4 genre, ~4 decade, ~4 director, ~4 keyword, ~4 low_rated, ~4 high_vote_count
        # But adjust based on pool sizes
        target_per_type = 4
        gi, di, dri, ki = 0, 0, 0, 0

        for _ in range(target_per_type):
            if gi < len(genre_pool):
                g = genre_pool[gi]
                _add("genre", f"A {g} movie", g)
                gi += 1

        for _ in range(target_per_type):
            if di < len(decade_pool):
                d = int(decade_pool[di])
                _add("decade", f"A movie from the {d}s", str(d))
                di += 1

        for _ in range(target_per_type):
            if dri < len(director_pool):
                dr = director_pool[dri]
                _add("director", f"A movie directed by {dr}", dr)
                dri += 1

        for _ in range(target_per_type):
            if ki < len(keyword_pool):
                k = keyword_pool[ki]
                _add("keyword", f"A movie with '{k}' theme", k)
                ki += 1

        # Add low_rated and high_vote_count (no parameter variation needed, just different labels)
        low_rated_labels = [
            ("A movie rated below 6 on TMDb", "below_6"),
            ("A critically underrated film (below 5.5)", "below_5.5"),
            ("A guilty pleasure (below 5 on TMDb)", "below_5"),
            ("A polarizing film (below 6.5 on TMDb)", "below_6.5"),
        ]
        high_vote_labels = [
            ("A blockbuster (1000+ votes)", "1000"),
            ("A popular movie (500+ votes)", "500"),
            ("A well-known film (2000+ votes)", "2000"),
            ("A mainstream hit (750+ votes)", "750"),
        ]

        rng.shuffle(low_rated_labels)
        rng.shuffle(high_vote_labels)

        for label, param in low_rated_labels[:target_per_type]:
            _add("low_rated", label, param)

        for label, param in high_vote_labels[:target_per_type]:
            _add("high_vote_count", label, param)

        # If we have fewer than 24, fill from remaining pools
        remaining_pools = [
            ("genre", genre_pool[gi:], lambda g: (f"A {g} movie", g)),
            ("decade", decade_pool[di:], lambda d: (f"A movie from the {int(d)}s", str(int(d)))),
            ("director", director_pool[dri:], lambda dr: (f"A movie directed by {dr}", dr)),
            ("keyword", keyword_pool[ki:], lambda k: (f"A movie with '{k}' theme", k)),
        ]
        rng.shuffle(remaining_pools)
        for tpl, pool, make_label in remaining_pools:
            for item in pool:
                if len(templates) >= 24:
                    break
                label, param = make_label(item)
                _add(tpl, label, param)

        # Trim to exactly 24 and shuffle
        templates = templates[:24]
        rng.shuffle(templates)

        # Insert FREE cell at index 12
        cells = []
        ti = 0
        for i in range(_GRID_SIZE):
            if i == _FREE_INDEX:
                cells.append(
                    {
                        "index": i,
                        "template": "free",
                        "label": "FREE",
                        "parameter": None,
                        "completed": True,
                        "movie_id": None,
                    }
                )
            else:
                cells.append(
                    {
                        "index": i,
                        "template": templates[ti]["template"],
                        "label": templates[ti]["label"],
                        "parameter": templates[ti]["parameter"],
                        "completed": False,
                        "movie_id": None,
                    }
                )
                ti += 1

        return cells

    async def _check_progress(
        self, user_id: int, cells: list[dict[str, Any]], db: AsyncSession
    ) -> None:
        """Mark cells as completed based on user's all-time ratings."""
        # Group cells by template type for batch queries
        by_template: dict[str, list[dict[str, Any]]] = {}
        for cell in cells:
            if cell["template"] == "free":
                continue
            by_template.setdefault(cell["template"], []).append(cell)

        # Genre cells
        for cell in by_template.get("genre", []):
            result = await db.execute(
                text(
                    "SELECT r.movie_id FROM ratings r "
                    "JOIN movies m ON r.movie_id = m.id "
                    "WHERE r.user_id = :uid "
                    "AND m.genres @> CAST(:genre_json AS jsonb) "
                    "LIMIT 1"
                ),
                {"uid": user_id, "genre_json": json.dumps([cell["parameter"]])},
            )
            row = result.first()
            if row:
                cell["completed"] = True
                cell["movie_id"] = row[0]

        # Decade cells
        for cell in by_template.get("decade", []):
            decade_int = int(cell["parameter"])
            result = await db.execute(
                text(
                    "SELECT r.movie_id FROM ratings r "
                    "JOIN movies m ON r.movie_id = m.id "
                    "WHERE r.user_id = :uid "
                    "AND m.release_date IS NOT NULL "
                    "AND EXTRACT(DECADE FROM m.release_date)::int * 10 = :decade "
                    "LIMIT 1"
                ),
                {"uid": user_id, "decade": decade_int},
            )
            row = result.first()
            if row:
                cell["completed"] = True
                cell["movie_id"] = row[0]

        # Director cells
        for cell in by_template.get("director", []):
            result = await db.execute(
                text(
                    "SELECT r.movie_id FROM ratings r "
                    "JOIN movies m ON r.movie_id = m.id "
                    "WHERE r.user_id = :uid "
                    "AND m.director = :director "
                    "LIMIT 1"
                ),
                {"uid": user_id, "director": cell["parameter"]},
            )
            row = result.first()
            if row:
                cell["completed"] = True
                cell["movie_id"] = row[0]

        # Keyword cells
        for cell in by_template.get("keyword", []):
            result = await db.execute(
                text(
                    "SELECT r.movie_id FROM ratings r "
                    "JOIN movies m ON r.movie_id = m.id "
                    "WHERE r.user_id = :uid "
                    "AND m.keywords @> CAST(:kw_json AS jsonb) "
                    "LIMIT 1"
                ),
                {"uid": user_id, "kw_json": json.dumps([cell["parameter"]])},
            )
            row = result.first()
            if row:
                cell["completed"] = True
                cell["movie_id"] = row[0]

        # Low-rated cells
        for cell in by_template.get("low_rated", []):
            threshold = float(cell["parameter"].replace("below_", ""))
            result = await db.execute(
                text(
                    "SELECT r.movie_id FROM ratings r "
                    "JOIN movies m ON r.movie_id = m.id "
                    "WHERE r.user_id = :uid "
                    "AND m.vote_average < :threshold "
                    "LIMIT 1"
                ),
                {"uid": user_id, "threshold": threshold},
            )
            row = result.first()
            if row:
                cell["completed"] = True
                cell["movie_id"] = row[0]

        # High vote count cells
        for cell in by_template.get("high_vote_count", []):
            min_votes = int(cell["parameter"])
            result = await db.execute(
                text(
                    "SELECT r.movie_id FROM ratings r "
                    "JOIN movies m ON r.movie_id = m.id "
                    "WHERE r.user_id = :uid "
                    "AND m.vote_count >= :min_votes "
                    "LIMIT 1"
                ),
                {"uid": user_id, "min_votes": min_votes},
            )
            row = result.first()
            if row:
                cell["completed"] = True
                cell["movie_id"] = row[0]

    @staticmethod
    def _check_lines(cells: list[dict[str, Any]]) -> list[list[int]]:
        """Return list of completed bingo lines (each is a list of 5 indices)."""
        completed_lines = []
        for line in _LINES:
            if all(cells[i]["completed"] for i in line):
                completed_lines.append(line)
        return completed_lines

    async def get_user_bingo(self, user_id: int, seed: str, db: AsyncSession) -> dict[str, Any]:
        """Generate a bingo card and check user progress."""
        rng = random.Random(_month_seed(seed))
        pools = await self._get_parameter_pools(db)
        cells = self._build_cells(rng, pools)

        await self._check_progress(user_id, cells, db)

        completed_lines = self._check_lines(cells)
        total_completed = sum(1 for c in cells if c["completed"])

        return {
            "user_id": user_id,
            "seed": seed,
            "cells": cells,
            "completed_lines": completed_lines,
            "total_completed": total_completed,
            "bingo_count": len(completed_lines),
        }
