"""LLM service for generating recommendation explanations via Ollama."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

import httpx

from cinematch.core.exceptions import ServiceUnavailableError

if TYPE_CHECKING:
    from cinematch.models.movie import Movie

logger = logging.getLogger(__name__)


class LLMService:
    """Async client for Ollama LLM API to generate recommendation explanations and re-ranking."""

    def __init__(self, base_url: str, model_name: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._client = httpx.AsyncClient(timeout=timeout)

    async def explain_recommendation(
        self,
        movie: Movie,
        user_top_rated: list[tuple[str, float]],
        score: float,
    ) -> str:
        """Generate a natural language explanation for why a movie was recommended."""
        prompt = self._build_prompt(movie, user_top_rated, score)

        try:
            resp = await self._client.post(
                f"{self._base_url}/api/generate",
                json={"model": self._model_name, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Ollama request failed: %s", e)
            raise ServiceUnavailableError("LLM service (Ollama)") from e
        except httpx.HTTPStatusError as e:
            logger.warning("Ollama returned HTTP %s: %s", e.response.status_code, e)
            raise ServiceUnavailableError("LLM service (Ollama)") from e

        data = resp.json()
        explanation = data.get("response")
        if not explanation:
            logger.warning("Ollama response missing 'response' field: %s", data)
            return "Explanation unavailable."

        return explanation.strip()

    async def rerank_candidates(
        self,
        candidates: list[dict],
        user_history: list[dict],
    ) -> list[int] | None:
        """Ask the LLM to re-rank recommendation candidates.

        Returns an ordered list of movie IDs, or None if parsing fails.
        """
        prompt = self._build_rerank_prompt(candidates, user_history)

        try:
            resp = await self._client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Ollama rerank request failed: %s", e)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("Ollama rerank returned HTTP %s: %s", e.response.status_code, e)
            return None

        data = resp.json()
        response_text = data.get("response", "")
        return self._parse_rerank_response(response_text, {c["id"] for c in candidates})

    @staticmethod
    def _build_rerank_prompt(
        candidates: list[dict],
        user_history: list[dict],
    ) -> str:
        history_lines = "\n".join(f"- {h['title']} (rated {h['rating']}/10)" for h in user_history)
        candidate_lines = "\n".join(
            f"- ID:{c['id']} | {c['title']} | "
            f"Genres: {', '.join(c['genres']) if c['genres'] else 'Unknown'} | "
            f"Score: {c['score']}"
            for c in candidates
        )
        return (
            "You are a movie recommendation expert. Re-rank the following "
            "candidate movies for a user based on their viewing history.\n\n"
            "GOALS:\n"
            "1. Prioritize thematic and tonal variety — avoid clustering on one genre.\n"
            "2. Penalize sequels and franchise entries — prefer unique, standalone films "
            "over sequels of movies the user already watched.\n"
            "3. Match deeper thematic patterns the user enjoys, not just surface-level genres.\n"
            "4. Put the BEST recommendations first.\n\n"
            f"User's top-rated movies:\n{history_lines}\n\n"
            f"Candidate movies to re-rank:\n{candidate_lines}\n\n"
            'Return a JSON object with a single key "ranked_ids" containing an array '
            "of movie IDs (integers) in your recommended order, best first. "
            "Only include IDs from the candidate list above. Example: "
            '{"ranked_ids": [42, 17, 8, 103]}'
        )

    @staticmethod
    def _parse_rerank_response(response_text: str, valid_ids: set[int]) -> list[int] | None:
        """Parse the LLM's JSON response into a list of movie IDs."""
        if not response_text:
            return None

        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, dict) and "ranked_ids" in parsed:
                ids = parsed["ranked_ids"]
            elif isinstance(parsed, list):
                ids = parsed
            else:
                return None
        except json.JSONDecodeError:
            # Try extracting a JSON array from the text
            match = re.search(r"\[[\d,\s]+\]", response_text)
            if match:
                try:
                    ids = json.loads(match.group())
                except json.JSONDecodeError:
                    return None
            else:
                return None

        # Validate: must be a list of ints from the candidate set
        result = []
        for item in ids:
            try:
                mid = int(item)
            except (ValueError, TypeError):
                continue
            if mid in valid_ids and mid not in result:
                result.append(mid)

        return result if result else None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    @staticmethod
    def _build_prompt(
        movie: Movie,
        user_top_rated: list[tuple[str, float]],
        score: float,
    ) -> str:
        genres = ", ".join(movie.genres) if movie.genres else "Unknown"
        overview = movie.overview or "No overview available"

        rated_lines = "\n".join(f"- {title} (rated {rating}/10)" for title, rating in user_top_rated)

        return (
            "You are a movie recommendation assistant. Explain why this movie "
            "was recommended based on the user's viewing history.\n\n"
            f"Recommended movie:\n"
            f"- Title: {movie.title}\n"
            f"- Genres: {genres}\n"
            f"- Overview: {overview}\n"
            f"- Recommendation score: {score:.2f}\n\n"
            f"User's top-rated movies:\n{rated_lines}\n\n"
            "In 2-3 sentences, explain why this movie is a good match for this "
            "user. Be specific about genre and thematic connections."
        )
