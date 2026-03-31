"""Taste profile service — generates natural-language summaries of user taste."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, text

from cinematch.models.rating import Rating

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.llm_service import LLMService
    from cinematch.services.user_stats_service import UserStatsService

logger = logging.getLogger(__name__)


class TasteProfileService:
    """Generate a structured taste profile with template-based insights."""

    def __init__(
        self,
        user_stats_service: UserStatsService,
        llm_service: LLMService | None = None,
    ) -> None:
        self._stats = user_stats_service
        self._llm = llm_service

    async def get_taste_profile(self, user_id: int, db: AsyncSession) -> dict[str, Any]:
        """Return a taste profile dict matching TasteProfileResponse."""
        stats = await self._stats.get_user_stats(user_id, db)
        total = stats["total_ratings"]

        if total == 0:
            return {
                "user_id": user_id,
                "total_ratings": 0,
                "insights": [],
                "llm_summary": None,
            }

        insights: list[dict[str, str]] = []

        # 1. Top genre
        genre_dist = stats.get("genre_distribution", [])
        if genre_dist:
            top = genre_dist[0]
            insights.append(
                {
                    "key": "top_genre",
                    "icon": "movie_filter",
                    "text": (
                        f"You're a {top['genre']} enthusiast ({top['percentage']}% of your ratings)"
                    ),
                }
            )

        # 2. Critic style (user avg vs global avg)
        user_avg = stats["average_rating"]
        global_avg = await self._get_global_average(db)
        label = self._critic_label(user_avg, global_avg)
        insights.append(
            {
                "key": "critic_style",
                "icon": "thumbs_up_down",
                "text": (
                    f"You're a {label} critic (avg {user_avg:.1f} vs site avg {global_avg:.1f})"
                ),
            }
        )

        # 3. Director affinity
        directors = stats.get("top_directors", [])
        if directors and directors[0]["count"] >= 2:
            d = directors[0]
            insights.append(
                {
                    "key": "director_affinity",
                    "icon": "person",
                    "text": (
                        f"You have a special appreciation for {d['name']}'s work "
                        f"({d['count']} films rated)"
                    ),
                }
            )

        # 4. Decade preference
        decade = await self._get_top_decade(user_id, db)
        if decade is not None:
            insights.append(
                {
                    "key": "decade_preference",
                    "icon": "calendar_month",
                    "text": f"Your sweet spot is {decade}s cinema",
                }
            )

        # Optional LLM summary
        llm_summary = None
        if self._llm is not None:
            llm_summary = await self._generate_llm_summary(stats, insights)

        return {
            "user_id": user_id,
            "total_ratings": total,
            "insights": insights,
            "llm_summary": llm_summary,
        }

    @staticmethod
    async def _get_global_average(db: AsyncSession) -> float:
        result = await db.execute(select(func.coalesce(func.avg(Rating.rating), 0)))
        return round(float(result.scalar_one()), 1)

    @staticmethod
    async def _get_top_decade(user_id: int, db: AsyncSession) -> int | None:
        stmt = text(
            "SELECT (EXTRACT(YEAR FROM m.release_date)::int / 10 * 10) AS decade, "
            "COUNT(*)::int AS cnt "
            "FROM ratings r "
            "JOIN movies m ON r.movie_id = m.id "
            "WHERE r.user_id = :uid AND m.release_date IS NOT NULL "
            "GROUP BY decade "
            "ORDER BY cnt DESC "
            "LIMIT 1"
        )
        result = await db.execute(stmt, {"uid": user_id})
        row = result.first()
        return int(row[0]) if row else None

    @staticmethod
    def _critic_label(user_avg: float, global_avg: float) -> str:
        if user_avg > global_avg + 0.5:
            return "generous"
        if user_avg < global_avg - 0.5:
            return "tough"
        return "balanced"

    async def _generate_llm_summary(
        self,
        stats: dict[str, Any],
        insights: list[dict[str, str]],
    ) -> str | None:
        insight_lines = "\n".join(f"- {i['text']}" for i in insights)
        genres = ", ".join(g["genre"] for g in stats.get("genre_distribution", [])[:5])
        directors = ", ".join(d["name"] for d in stats.get("top_directors", [])[:3])
        actors = ", ".join(a["name"] for a in stats.get("top_actors", [])[:3])

        prompt = (
            "You are a witty film critic writing a short taste profile for a movie fan.\n\n"
            f"Stats:\n"
            f"- Total films rated: {stats['total_ratings']}\n"
            f"- Average rating: {stats['average_rating']}/10\n"
            f"- Top genres: {genres}\n"
            f"- Favorite directors: {directors}\n"
            f"- Favorite actors: {actors}\n\n"
            f"Insights:\n{insight_lines}\n\n"
            "Write a 2-3 sentence personality-driven summary of this person's movie taste. "
            "Be playful and specific. Do not repeat the raw numbers."
        )

        try:
            resp = await self._llm._client.post(
                f"{self._llm._base_url}/api/generate",
                json={"model": self._llm._model_name, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            summary = data.get("response", "").strip()
            return summary if summary else None
        except Exception:
            logger.warning("LLM taste profile summary failed", exc_info=True)
            return None
