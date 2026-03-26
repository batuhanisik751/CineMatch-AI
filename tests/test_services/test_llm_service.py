"""Tests for the LLM service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cinematch.core.exceptions import ServiceUnavailableError
from cinematch.services.llm_service import LLMService


def _make_movie(
    title: str = "The Matrix",
    genres: list[str] | None = None,
    overview: str = "A computer hacker discovers reality is a simulation.",
) -> MagicMock:
    m = MagicMock()
    m.id = 1
    m.title = title
    m.genres = genres or ["Action", "Sci-Fi"]
    m.overview = overview
    return m


@pytest.fixture()
def llm_service() -> LLMService:
    return LLMService(base_url="http://localhost:11434", model_name="mistral")


@pytest.fixture()
def sample_movie() -> MagicMock:
    return _make_movie()


@pytest.fixture()
def user_top_rated() -> list[tuple[str, float]]:
    return [("Inception", 5.0), ("Blade Runner", 4.5), ("Interstellar", 4.0)]


async def test_explain_recommendation_success(llm_service, sample_movie, user_top_rated):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": "This movie matches your taste because of shared sci-fi themes."
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.92)

    assert result == "This movie matches your taste because of shared sci-fi themes."
    mock_post.assert_called_once()


async def test_explain_recommendation_ollama_timeout(llm_service, sample_movie, user_top_rated):
    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")
        with pytest.raises(ServiceUnavailableError):
            await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.9)


async def test_explain_recommendation_connection_error(llm_service, sample_movie, user_top_rated):
    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        with pytest.raises(ServiceUnavailableError):
            await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.9)


async def test_explain_recommendation_bad_response(llm_service, sample_movie, user_top_rated):
    mock_response = MagicMock()
    mock_response.json.return_value = {"model": "mistral"}
    mock_response.raise_for_status = MagicMock()

    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.9)

    assert result == "Explanation unavailable."


async def test_prompt_contains_movie_details(llm_service, sample_movie, user_top_rated):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Great match."}
    mock_response.raise_for_status = MagicMock()

    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.85)

    call_kwargs = mock_post.call_args
    if "json" in call_kwargs.kwargs:
        prompt = call_kwargs.kwargs["json"]["prompt"]
    else:
        prompt = call_kwargs[1]["json"]["prompt"]
    assert "The Matrix" in prompt
    assert "Action" in prompt
    assert "Sci-Fi" in prompt
    assert "Inception" in prompt
    assert "0.85" in prompt


async def test_close_closes_client(llm_service):
    with patch.object(llm_service._client, "aclose", new_callable=AsyncMock) as mock_close:
        await llm_service.close()
        mock_close.assert_called_once()
