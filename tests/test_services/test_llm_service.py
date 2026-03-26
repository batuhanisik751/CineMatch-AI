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


# ------------------------------------------------------------------
# Rerank candidate tests
# ------------------------------------------------------------------


@pytest.fixture()
def sample_candidates():
    return [
        {"id": 10, "title": "Cars", "genres": ["Animation"], "score": 0.9},
        {"id": 20, "title": "Inception", "genres": ["Sci-Fi"], "score": 0.8},
        {"id": 30, "title": "Toy Story", "genres": ["Animation"], "score": 0.7},
    ]


@pytest.fixture()
def sample_history():
    return [{"title": "The Matrix", "rating": 5.0}]


async def test_rerank_candidates_success(llm_service, sample_candidates, sample_history):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": '{"ranked_ids": [20, 10, 30]}'}
    mock_response.raise_for_status = MagicMock()

    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await llm_service.rerank_candidates(sample_candidates, sample_history)

    assert result == [20, 10, 30]


async def test_rerank_candidates_timeout_returns_none(
    llm_service, sample_candidates, sample_history
):
    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timed out")
        result = await llm_service.rerank_candidates(sample_candidates, sample_history)

    assert result is None


async def test_rerank_candidates_connection_error_returns_none(
    llm_service, sample_candidates, sample_history
):
    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Refused")
        result = await llm_service.rerank_candidates(sample_candidates, sample_history)

    assert result is None


async def test_rerank_candidates_bad_json_returns_none(
    llm_service, sample_candidates, sample_history
):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "I cannot parse this"}
    mock_response.raise_for_status = MagicMock()

    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await llm_service.rerank_candidates(sample_candidates, sample_history)

    assert result is None


def test_parse_rerank_response_valid_json():
    valid_ids = {10, 20, 30}
    result = LLMService._parse_rerank_response('{"ranked_ids": [20, 10, 30]}', valid_ids)
    assert result == [20, 10, 30]


def test_parse_rerank_response_plain_array():
    valid_ids = {10, 20, 30}
    result = LLMService._parse_rerank_response("[20, 10, 30]", valid_ids)
    assert result == [20, 10, 30]


def test_parse_rerank_response_filters_invalid_ids():
    valid_ids = {10, 20}
    result = LLMService._parse_rerank_response('{"ranked_ids": [20, 999, 10]}', valid_ids)
    assert result == [20, 10]


def test_parse_rerank_response_empty_returns_none():
    assert LLMService._parse_rerank_response("", {10, 20}) is None


def test_parse_rerank_response_garbage_returns_none():
    assert LLMService._parse_rerank_response("not json at all", {10, 20}) is None


def test_parse_rerank_response_extracts_array_from_text():
    valid_ids = {10, 20, 30}
    result = LLMService._parse_rerank_response(
        "Here are the results: [20, 10, 30] hope that helps!", valid_ids
    )
    assert result == [20, 10, 30]


def test_rerank_prompt_contains_candidates(llm_service):
    candidates = [
        {"id": 10, "title": "Cars", "genres": ["Animation"], "score": 0.9},
    ]
    history = [{"title": "The Matrix", "rating": 5.0}]
    prompt = LLMService._build_rerank_prompt(candidates, history)
    assert "Cars" in prompt
    assert "The Matrix" in prompt
    assert "ID:10" in prompt
    assert "ranked_ids" in prompt
