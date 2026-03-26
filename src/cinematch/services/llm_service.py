"""LLM service for generating recommendation explanations via Ollama."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from cinematch.core.exceptions import ServiceUnavailableError

if TYPE_CHECKING:
    from cinematch.models.movie import Movie

logger = logging.getLogger(__name__)


class LLMService:
    """Async client for Ollama LLM API to generate recommendation explanations."""

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

        rated_lines = "\n".join(f"- {title} (rated {rating}/5)" for title, rating in user_top_rated)

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
