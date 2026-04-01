"""Achievement badge computation service."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

BADGE_DEFS: list[dict[str, Any]] = [
    {
        "id": "first_rating",
        "name": "First Rating",
        "description": "Rate your first movie",
        "icon": "star",
        "target": 1,
    },
    {
        "id": "century_club",
        "name": "Century Club",
        "description": "Rate 100 movies",
        "icon": "military_tech",
        "target": 100,
    },
    {
        "id": "marathon_runner",
        "name": "Marathon Runner",
        "description": "Rate 500 movies",
        "icon": "sprint",
        "target": 500,
    },
    {
        "id": "genre_explorer",
        "name": "Genre Explorer",
        "description": "Rate movies in 10+ different genres",
        "icon": "explore",
        "target": 10,
    },
    {
        "id": "decade_hopper",
        "name": "Decade Hopper",
        "description": "Rate movies from 5+ different decades",
        "icon": "history",
        "target": 5,
    },
    {
        "id": "director_devotee",
        "name": "Director Devotee",
        "description": "Rate 5+ movies by the same director",
        "icon": "loyalty",
        "target": 5,
    },
    {
        "id": "the_critic",
        "name": "The Critic",
        "description": "Average rating below 5.0 with 50+ ratings",
        "icon": "thumb_down",
        "target": 50,
    },
    {
        "id": "easy_to_please",
        "name": "Easy to Please",
        "description": "Average rating above 8.0 with 50+ ratings",
        "icon": "thumb_up",
        "target": 50,
    },
    {
        "id": "weekend_warrior",
        "name": "Weekend Warrior",
        "description": "Rate 5+ movies in a single weekend",
        "icon": "weekend",
        "target": 5,
    },
    {
        "id": "night_owl",
        "name": "Night Owl",
        "description": "10+ ratings submitted between midnight and 5am",
        "icon": "dark_mode",
        "target": 10,
    },
    {
        "id": "streak_master",
        "name": "Streak Master",
        "description": "Maintain a 7-day rating streak",
        "icon": "local_fire_department",
        "target": 7,
    },
    {
        "id": "completionist",
        "name": "Completionist",
        "description": "Rate every movie by a director (min 5 in DB)",
        "icon": "task_alt",
        "target": 1,
    },
]


class AchievementService:
    """Computes achievement badges from user rating history."""

    async def get_achievements(self, user_id: int, db: AsyncSession) -> dict[str, Any]:
        # Query A: basic stats
        basic = await db.execute(
            text(
                "SELECT COUNT(*)::int AS total, "
                "COALESCE(AVG(rating), 0)::float AS avg_r "
                "FROM ratings WHERE user_id = :uid"
            ),
            {"uid": user_id},
        )
        row_a = basic.one()
        total_ratings: int = row_a[0]
        avg_rating: float = row_a[1]

        # Query B: distinct genre count
        genre_result = await db.execute(
            text(
                "SELECT COUNT(DISTINCT genre)::int AS cnt "
                "FROM ratings r "
                "JOIN movies m ON r.movie_id = m.id, "
                "jsonb_array_elements_text(m.genres) AS genre "
                "WHERE r.user_id = :uid"
            ),
            {"uid": user_id},
        )
        genre_count: int = genre_result.scalar_one()

        # Query C: distinct decade count
        decade_result = await db.execute(
            text(
                "SELECT COUNT(DISTINCT EXTRACT(DECADE FROM m.release_date))::int AS cnt "
                "FROM ratings r "
                "JOIN movies m ON r.movie_id = m.id "
                "WHERE r.user_id = :uid AND m.release_date IS NOT NULL"
            ),
            {"uid": user_id},
        )
        decade_count: int = decade_result.scalar_one()

        # Query D: director stats (devotee + completionist)
        director_result = await db.execute(
            text(
                "WITH user_directors AS ( "
                "    SELECT m.director, COUNT(*)::int AS rated_cnt "
                "    FROM ratings r "
                "    JOIN movies m ON r.movie_id = m.id "
                "    WHERE r.user_id = :uid AND m.director IS NOT NULL "
                "    GROUP BY m.director "
                "), "
                "db_directors AS ( "
                "    SELECT director, COUNT(*)::int AS total_cnt "
                "    FROM movies "
                "    WHERE director IS NOT NULL "
                "    GROUP BY director "
                "    HAVING COUNT(*) >= 5 "
                ") "
                "SELECT ud.director, ud.rated_cnt, COALESCE(dd.total_cnt, 0) AS total_cnt "
                "FROM user_directors ud "
                "LEFT JOIN db_directors dd ON ud.director = dd.director "
                "ORDER BY ud.rated_cnt DESC"
            ),
            {"uid": user_id},
        )
        director_rows = director_result.all()

        max_director_count = 0
        top_director_name: str | None = None
        completionist_unlocked = False
        completionist_director: str | None = None

        for drow in director_rows:
            director_name = drow[0]
            rated_cnt = drow[1]
            total_cnt = drow[2]

            if rated_cnt > max_director_count:
                max_director_count = rated_cnt
                top_director_name = director_name

            if total_cnt >= 5 and rated_cnt >= total_cnt and not completionist_unlocked:
                completionist_unlocked = True
                completionist_director = director_name

        # Query E: timestamp-based badges (night owl, weekend warrior, streak)
        ts_result = await db.execute(
            text(
                "WITH rating_meta AS ( "
                "    SELECT "
                "        DATE(timestamp AT TIME ZONE 'UTC') AS d, "
                "        EXTRACT(DOW FROM timestamp AT TIME ZONE 'UTC')::int AS dow, "
                "        EXTRACT(HOUR FROM timestamp AT TIME ZONE 'UTC')::int AS hr "
                "    FROM ratings "
                "    WHERE user_id = :uid "
                "), "
                "night_count AS ( "
                "    SELECT COUNT(*)::int AS cnt FROM rating_meta WHERE hr >= 0 AND hr < 5 "
                "), "
                "weekend_groups AS ( "
                "    SELECT "
                "        DATE_TRUNC('week', d + INTERVAL '1 day') AS wk, "
                "        COUNT(*)::int AS cnt "
                "    FROM rating_meta "
                "    WHERE dow IN (0, 6) "
                "    GROUP BY wk "
                "), "
                "best_weekend AS ( "
                "    SELECT COALESCE(MAX(cnt), 0)::int AS max_wk FROM weekend_groups "
                "), "
                "rating_dates AS ( "
                "    SELECT DISTINCT d FROM rating_meta "
                "), "
                "grouped AS ( "
                "    SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d))::int * INTERVAL '1 day' AS grp "
                "    FROM rating_dates "
                "), "
                "streaks AS ( "
                "    SELECT COUNT(*)::int AS streak_len FROM grouped GROUP BY grp "
                "), "
                "max_streak AS ( "
                "    SELECT COALESCE(MAX(streak_len), 0)::int AS longest FROM streaks "
                ") "
                "SELECT "
                "    (SELECT cnt FROM night_count) AS night_owl_count, "
                "    (SELECT max_wk FROM best_weekend) AS best_weekend_count, "
                "    (SELECT longest FROM max_streak) AS longest_streak"
            ),
            {"uid": user_id},
        )
        row_e = ts_result.one()
        night_owl_count: int = row_e[0]
        best_weekend_count: int = row_e[1]
        longest_streak: int = row_e[2]

        # Build badge results
        progress_map: dict[str, tuple[int, bool, str | None]] = {
            "first_rating": (
                min(total_ratings, 1),
                total_ratings >= 1,
                None,
            ),
            "century_club": (
                min(total_ratings, 100),
                total_ratings >= 100,
                None,
            ),
            "marathon_runner": (
                min(total_ratings, 500),
                total_ratings >= 500,
                None,
            ),
            "genre_explorer": (
                min(genre_count, 10),
                genre_count >= 10,
                f"{genre_count} genres" if genre_count >= 10 else None,
            ),
            "decade_hopper": (
                min(decade_count, 5),
                decade_count >= 5,
                f"{decade_count} decades" if decade_count >= 5 else None,
            ),
            "director_devotee": (
                min(max_director_count, 5),
                max_director_count >= 5,
                f"{top_director_name} ({max_director_count} films)"
                if max_director_count >= 5
                else None,
            ),
            "the_critic": (
                min(total_ratings, 50),
                avg_rating < 5.0 and total_ratings >= 50,
                f"Avg: {avg_rating:.1f}" if avg_rating < 5.0 and total_ratings >= 50 else None,
            ),
            "easy_to_please": (
                min(total_ratings, 50),
                avg_rating > 8.0 and total_ratings >= 50,
                f"Avg: {avg_rating:.1f}" if avg_rating > 8.0 and total_ratings >= 50 else None,
            ),
            "weekend_warrior": (
                min(best_weekend_count, 5),
                best_weekend_count >= 5,
                None,
            ),
            "night_owl": (
                min(night_owl_count, 10),
                night_owl_count >= 10,
                f"{night_owl_count} late-night ratings" if night_owl_count >= 10 else None,
            ),
            "streak_master": (
                min(longest_streak, 7),
                longest_streak >= 7,
                f"{longest_streak}-day streak" if longest_streak >= 7 else None,
            ),
            "completionist": (
                1 if completionist_unlocked else 0,
                completionist_unlocked,
                completionist_director if completionist_unlocked else None,
            ),
        }

        badges = []
        for bdef in BADGE_DEFS:
            bid = bdef["id"]
            progress, unlocked, detail = progress_map[bid]
            badges.append(
                {
                    "id": bid,
                    "name": bdef["name"],
                    "description": bdef["description"],
                    "icon": bdef["icon"],
                    "unlocked": unlocked,
                    "progress": progress,
                    "target": bdef["target"],
                    "unlocked_detail": detail,
                }
            )

        unlocked_count = sum(1 for b in badges if b["unlocked"])
        return {
            "user_id": user_id,
            "badges": badges,
            "unlocked_count": unlocked_count,
            "total_count": len(BADGE_DEFS),
        }
