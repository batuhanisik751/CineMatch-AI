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


# ------------------------------------------------------------------
# Ollama backend fixtures and tests
# ------------------------------------------------------------------


@pytest.fixture()
def llm_service() -> LLMService:
    return LLMService(base_url="http://localhost:11434", model_name="mistral", backend="ollama")


@pytest.fixture()
def groq_service() -> LLMService:
    return LLMService(
        base_url="https://api.groq.com",
        model_name="llama-3.1-8b-instant",
        backend="groq",
        api_key="gsk_test_key",
    )


@pytest.fixture()
def sample_movie() -> MagicMock:
    return _make_movie()


@pytest.fixture()
def user_top_rated() -> list[tuple[str, float]]:
    return [("Inception", 10), ("Blade Runner", 9), ("Interstellar", 8)]


# ------------------------------------------------------------------
# generate() — Ollama backend
# ------------------------------------------------------------------


async def test_generate_ollama_success(llm_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Hello world"}
    mock_response.raise_for_status = MagicMock()

    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await llm_service.generate("Say hello")

    assert result == "Hello world"
    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1]["json"]
    assert payload["model"] == "mistral"
    assert payload["prompt"] == "Say hello"
    assert payload["stream"] is False
    assert "format" not in payload


async def test_generate_ollama_json_mode(llm_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": '{"key": "value"}'}
    mock_response.raise_for_status = MagicMock()

    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await llm_service.generate("Return JSON", json_mode=True)

    assert result == '{"key": "value"}'
    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1]["json"]
    assert payload["format"] == "json"


async def test_generate_ollama_timeout(llm_service):
    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")
        with pytest.raises(ServiceUnavailableError):
            await llm_service.generate("Say hello")


async def test_generate_ollama_connection_error(llm_service):
    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        with pytest.raises(ServiceUnavailableError):
            await llm_service.generate("Say hello")


async def test_generate_ollama_empty_response(llm_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {"model": "mistral"}
    mock_response.raise_for_status = MagicMock()

    with patch.object(llm_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await llm_service.generate("Say hello")

    assert result == ""


# ------------------------------------------------------------------
# generate() — Groq backend
# ------------------------------------------------------------------


async def test_generate_groq_success(groq_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "Hello from Groq"}}]}
    mock_response.raise_for_status = MagicMock()

    with patch.object(groq_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await groq_service.generate("Say hello")

    assert result == "Hello from Groq"
    call_kwargs = mock_post.call_args
    url = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("url", "")
    assert "/openai/v1/chat/completions" in str(url)
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1]["json"]
    assert payload["model"] == "llama-3.1-8b-instant"
    assert payload["messages"] == [{"role": "user", "content": "Say hello"}]
    assert "response_format" not in payload


async def test_generate_groq_json_mode(groq_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"ranked_ids": [1, 2]}'}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(groq_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await groq_service.generate("Return JSON", json_mode=True)

    assert result == '{"ranked_ids": [1, 2]}'
    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1]["json"]
    assert payload["response_format"] == {"type": "json_object"}


async def test_generate_groq_timeout(groq_service):
    with patch.object(groq_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timed out")
        with pytest.raises(ServiceUnavailableError):
            await groq_service.generate("Say hello")


async def test_generate_groq_connection_error(groq_service):
    with patch.object(groq_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        with pytest.raises(ServiceUnavailableError):
            await groq_service.generate("Say hello")


async def test_generate_groq_empty_choices(groq_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": []}
    mock_response.raise_for_status = MagicMock()

    with patch.object(groq_service._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await groq_service.generate("Say hello")

    assert result == ""


async def test_groq_api_key_in_headers(groq_service):
    assert groq_service._client.headers["Authorization"] == "Bearer gsk_test_key"


async def test_ollama_no_auth_header(llm_service):
    assert "Authorization" not in llm_service._client.headers


# ------------------------------------------------------------------
# explain_recommendation (uses generate internally)
# ------------------------------------------------------------------


async def test_explain_recommendation_success(llm_service, sample_movie, user_top_rated):
    with patch.object(llm_service, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "This movie matches your taste because of shared sci-fi themes."
        result = await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.92)

    assert result == "This movie matches your taste because of shared sci-fi themes."
    mock_gen.assert_called_once()


async def test_explain_recommendation_timeout(llm_service, sample_movie, user_top_rated):
    with patch.object(llm_service, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = ServiceUnavailableError("LLM service (Ollama)")
        with pytest.raises(ServiceUnavailableError):
            await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.9)


async def test_explain_recommendation_empty_response(llm_service, sample_movie, user_top_rated):
    with patch.object(llm_service, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = ""
        result = await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.9)

    assert result == "Explanation unavailable."


async def test_prompt_contains_movie_details(llm_service, sample_movie, user_top_rated):
    with patch.object(llm_service, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Great match."
        await llm_service.explain_recommendation(sample_movie, user_top_rated, 0.85)

    prompt = mock_gen.call_args[0][0]
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
    return [{"title": "The Matrix", "rating": 10}]


async def test_rerank_candidates_success(llm_service, sample_candidates, sample_history):
    with patch.object(llm_service, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = '{"ranked_ids": [20, 10, 30]}'
        result = await llm_service.rerank_candidates(sample_candidates, sample_history)

    assert result == [20, 10, 30]
    mock_gen.assert_called_once()
    # Verify json_mode=True was passed
    assert mock_gen.call_args.kwargs.get("json_mode") is True


async def test_rerank_candidates_timeout_returns_none(
    llm_service, sample_candidates, sample_history
):
    with patch.object(llm_service, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = httpx.TimeoutException("Timed out")
        result = await llm_service.rerank_candidates(sample_candidates, sample_history)

    assert result is None


async def test_rerank_candidates_connection_error_returns_none(
    llm_service, sample_candidates, sample_history
):
    with patch.object(llm_service, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = httpx.ConnectError("Refused")
        result = await llm_service.rerank_candidates(sample_candidates, sample_history)

    assert result is None


async def test_rerank_candidates_bad_json_returns_none(
    llm_service, sample_candidates, sample_history
):
    with patch.object(llm_service, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "I cannot parse this"
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


# ------------------------------------------------------------------
# Backend selection
# ------------------------------------------------------------------


async def test_default_backend_is_ollama():
    svc = LLMService(base_url="http://localhost:11434", model_name="mistral")
    assert svc._backend == "ollama"
    await svc.close()
