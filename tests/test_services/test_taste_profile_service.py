"""Tests for TasteProfileService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.taste_profile_service import TasteProfileService


def _make_stats(
    total: int = 20,
    avg: float = 7.2,
    top_genre: str = "Thriller",
    top_genre_pct: float = 35.0,
    top_director: str = "Christopher Nolan",
    top_director_count: int = 5,
) -> dict:
    return {
        "user_id": 1,
        "total_ratings": total,
        "average_rating": avg,
        "genre_distribution": [
            {"genre": top_genre, "count": 7, "percentage": top_genre_pct},
            {"genre": "Action", "count": 5, "percentage": 25.0},
        ],
        "rating_distribution": [{"rating": str(v), "count": 2} for v in range(1, 11)],
        "top_directors": [
            {"name": top_director, "count": top_director_count},
            {"name": "David Fincher", "count": 3},
        ],
        "top_actors": [
            {"name": "Leonardo DiCaprio", "count": 4},
            {"name": "Tom Hanks", "count": 3},
        ],
        "rating_timeline": [{"month": "2024-01", "count": 20}],
    }


@pytest.fixture()
def mock_user_stats():
    svc = AsyncMock()
    svc.get_user_stats.return_value = _make_stats()
    return svc


@pytest.fixture()
def service(mock_user_stats):
    return TasteProfileService(user_stats_service=mock_user_stats, llm_service=None)


@pytest.fixture()
def mock_db():
    db = AsyncMock()

    # Default: global avg = 6.5, top decade = 2000
    global_avg_result = MagicMock()
    global_avg_result.scalar_one.return_value = 6.5

    decade_result = MagicMock()
    decade_result.first.return_value = (2000, 15)

    db.execute = AsyncMock(side_effect=[global_avg_result, decade_result])
    return db


@pytest.mark.asyncio
async def test_full_profile_produces_all_insights(service, mock_db, mock_user_stats):
    """User with sufficient data gets all 4 insights."""
    # get_user_stats is called first, then global avg, then decade
    result = await service.get_taste_profile(1, mock_db)

    assert result["user_id"] == 1
    assert result["total_ratings"] == 20
    assert len(result["insights"]) == 4

    keys = [i["key"] for i in result["insights"]]
    assert keys == ["top_genre", "critic_style", "director_affinity", "decade_preference"]

    # Verify content
    assert "Thriller" in result["insights"][0]["text"]
    assert "35.0%" in result["insights"][0]["text"]
    assert "generous" in result["insights"][1]["text"]  # 7.2 > 6.5 + 0.5
    assert "Christopher Nolan" in result["insights"][2]["text"]
    assert "2000s" in result["insights"][3]["text"]


@pytest.mark.asyncio
async def test_empty_profile_for_zero_ratings(service, mock_db, mock_user_stats):
    """User with no ratings gets empty insights."""
    mock_user_stats.get_user_stats.return_value = _make_stats(total=0)

    result = await service.get_taste_profile(1, mock_db)

    assert result["total_ratings"] == 0
    assert result["insights"] == []
    assert result["llm_summary"] is None


@pytest.mark.asyncio
async def test_director_insight_skipped_when_count_below_threshold(
    service, mock_db, mock_user_stats
):
    """Director insight is excluded when top director has < 2 films."""
    mock_user_stats.get_user_stats.return_value = _make_stats(top_director_count=1)

    result = await service.get_taste_profile(1, mock_db)

    keys = [i["key"] for i in result["insights"]]
    assert "director_affinity" not in keys


@pytest.mark.asyncio
async def test_decade_insight_skipped_when_no_release_dates(service, mock_db, mock_user_stats):
    """Decade insight is excluded when no movies have release dates."""
    global_avg_result = MagicMock()
    global_avg_result.scalar_one.return_value = 6.5

    decade_result = MagicMock()
    decade_result.first.return_value = None  # No decade data

    mock_db.execute = AsyncMock(side_effect=[global_avg_result, decade_result])

    result = await service.get_taste_profile(1, mock_db)

    keys = [i["key"] for i in result["insights"]]
    assert "decade_preference" not in keys


@pytest.mark.asyncio
async def test_critic_label_generous():
    """User avg > global + 0.5 → generous."""
    assert TasteProfileService._critic_label(8.0, 6.5) == "generous"


@pytest.mark.asyncio
async def test_critic_label_tough():
    """User avg < global - 0.5 → tough."""
    assert TasteProfileService._critic_label(5.0, 6.5) == "tough"


@pytest.mark.asyncio
async def test_critic_label_balanced():
    """User avg within 0.5 of global → balanced."""
    assert TasteProfileService._critic_label(6.5, 6.5) == "balanced"
    assert TasteProfileService._critic_label(6.9, 6.5) == "balanced"
    assert TasteProfileService._critic_label(6.1, 6.5) == "balanced"


@pytest.mark.asyncio
async def test_llm_summary_generated_when_service_available(mock_user_stats, mock_db):
    """LLM summary is populated when llm_service is present and succeeds."""
    mock_llm = MagicMock()
    mock_llm._base_url = "http://localhost:11434"
    mock_llm._model_name = "mistral"

    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "You're a cinephile with great taste."}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_llm._client = mock_client

    service = TasteProfileService(user_stats_service=mock_user_stats, llm_service=mock_llm)

    result = await service.get_taste_profile(1, mock_db)

    assert result["llm_summary"] == "You're a cinephile with great taste."
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_none(mock_user_stats, mock_db):
    """LLM failure degrades gracefully to llm_summary=None."""
    mock_llm = MagicMock()
    mock_llm._base_url = "http://localhost:11434"
    mock_llm._model_name = "mistral"

    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("Connection refused")
    mock_llm._client = mock_client

    service = TasteProfileService(user_stats_service=mock_user_stats, llm_service=mock_llm)

    result = await service.get_taste_profile(1, mock_db)

    assert result["llm_summary"] is None
    assert len(result["insights"]) > 0  # Template insights still work
