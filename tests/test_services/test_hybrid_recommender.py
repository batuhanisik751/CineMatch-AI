"""Tests for HybridRecommender."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cinematch.services.hybrid_recommender import HybridRecommender


def _db_execute_factory(
    top_rated: list[tuple] | None = None,
    rated_ids: list[tuple] | None = None,
    titles: list[tuple] | None = None,
    genres: list[tuple] | None = None,
):
    """Build a side_effect list for mock db.execute calls.

    The hybrid pipeline calls db.execute in this order:
    1. _get_user_top_rated_diverse  (top rated with genres)
    2. _get_user_rated_movie_ids    (rated ids)
    3. _get_movie_titles            (seed titles)
    4. _get_movie_titles            (candidate titles)
    5. _get_movie_genres            (candidate genres for rerank)
    6. _get_movie_genres            (candidate genres for MMR fallback — sometimes)
    """
    if top_rated is None:
        top_rated = [(101, 5.0, ["Action", "Sci-Fi"])]
    if rated_ids is None:
        rated_ids = [(101,)]
    if titles is None:
        titles = [(102, "Movie B"), (103, "Movie C"), (104, "Movie D"), (105, "Movie E")]
    if genres is None:
        genres = [
            (102, ["Action"]),
            (103, ["Comedy"]),
            (104, ["Drama"]),
            (105, ["Sci-Fi"]),
        ]

    def _make_result(data):
        r = MagicMock()
        r.fetchall.return_value = data
        return r

    # Return enough results for all possible db.execute calls
    return [
        _make_result(top_rated),  # 1: top rated diverse
        _make_result(rated_ids),  # 2: rated ids
        _make_result([(101, "Movie A")] + titles),  # 3: seed titles
        _make_result(titles),  # 4: candidate titles
        _make_result(genres),  # 5: candidate genres (rerank)
        _make_result(genres),  # 6: candidate genres (MMR fallback)
    ]


@pytest.mark.asyncio
async def test_hybrid_recommend_combines_scores(hybrid_recommender, mock_db_session):
    """Hybrid should use both content and collab scores."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]

        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    assert len(results) > 0
    result_ids = [mid for mid, _ in results]
    assert 101 not in result_ids


@pytest.mark.asyncio
async def test_hybrid_recommend_cold_start_uses_content_only(hybrid_recommender, mock_db_session):
    """Cold-start user (unknown to ALS) should get content-only recs."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.85), (103, 0.75)]

        results = await hybrid_recommender.recommend(
            user_id=999, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    assert len(results) > 0


@pytest.mark.asyncio
async def test_hybrid_recommend_excludes_already_rated(hybrid_recommender, mock_db_session):
    mock_db_session.execute = AsyncMock(
        side_effect=_db_execute_factory(
            top_rated=[(101, 5.0, ["Action"]), (102, 4.0, ["Drama"])],
            rated_ids=[(101,), (102,)],
        )
    )

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(101, 0.99), (103, 0.8), (104, 0.7)]

        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    result_ids = [mid for mid, _ in results]
    assert 101 not in result_ids
    assert 102 not in result_ids


@pytest.mark.asyncio
async def test_content_only_strategy(hybrid_recommender, mock_db_session):
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]

        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="content"
        )

    assert len(results) > 0


@pytest.mark.asyncio
async def test_collab_only_strategy(hybrid_recommender, mock_db_session):
    results = await hybrid_recommender.recommend(
        user_id=1, db=mock_db_session, top_k=3, strategy="collab"
    )
    assert len(results) == 3
    result_ids = [mid for mid, _ in results]
    assert result_ids == [101, 103, 105]


@pytest.mark.asyncio
async def test_invalid_strategy_raises_value_error(hybrid_recommender, mock_db_session):
    with pytest.raises(ValueError, match="Unknown strategy"):
        await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="invalid"
        )


def test_min_max_normalize_standard_case():
    scores = {1: 0.2, 2: 0.8, 3: 0.5}
    normed = HybridRecommender._min_max_normalize(scores)
    assert normed[1] == pytest.approx(0.0)
    assert normed[2] == pytest.approx(1.0)
    assert normed[3] == pytest.approx(0.5)


def test_min_max_normalize_all_equal_returns_half():
    scores = {1: 0.5, 2: 0.5, 3: 0.5}
    normed = HybridRecommender._min_max_normalize(scores)
    assert all(v == 0.5 for v in normed.values())


def test_min_max_normalize_empty_dict():
    assert HybridRecommender._min_max_normalize({}) == {}


def test_min_max_normalize_single_value():
    scores = {1: 0.7}
    normed = HybridRecommender._min_max_normalize(scores)
    assert normed[1] == 0.5


@pytest.mark.asyncio
async def test_recommend_user_with_no_ratings_returns_empty(hybrid_recommender, mock_db_session):
    """User with no ratings and unknown to ALS gets empty results."""
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []

    mock_db_session.execute = AsyncMock(return_value=empty_result)

    results = await hybrid_recommender.recommend(
        user_id=999, db=mock_db_session, top_k=5, strategy="hybrid"
    )
    assert results == []


@pytest.mark.asyncio
async def test_hybrid_recommend_respects_top_k(hybrid_recommender, mock_db_session):
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8), (104, 0.7), (105, 0.6)]

        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=2, strategy="hybrid"
        )

    assert len(results) <= 2


# ------------------------------------------------------------------
# Franchise/sequel penalty tests
# ------------------------------------------------------------------


def test_base_title_strips_sequel_number():
    assert HybridRecommender._base_title("Cars 2") == "cars"
    assert HybridRecommender._base_title("Cars 3") == "cars"


def test_base_title_strips_colon_subtitle():
    assert HybridRecommender._base_title("Star Wars: A New Hope") == "star wars"
    assert HybridRecommender._base_title("Alien: Covenant") == "alien"


def test_base_title_strips_articles():
    assert HybridRecommender._base_title("The Matrix") == "matrix"
    assert HybridRecommender._base_title("A Beautiful Mind") == "beautiful mind"


def test_base_title_strips_roman_numerals():
    assert HybridRecommender._base_title("Rocky III") == "rocky"
    assert HybridRecommender._base_title("Mission Impossible II") == "mission impossible"


def test_base_title_no_false_positive():
    """Unrelated titles should not match."""
    assert HybridRecommender._base_title("The Dark Knight") != HybridRecommender._base_title(
        "The Dark Crystal"
    )


# ------------------------------------------------------------------
# MMR diversity re-ranking tests
# ------------------------------------------------------------------


def test_mmr_rerank_diversifies_genres():
    """MMR should prefer genre diversity over pure score ordering."""
    rec = HybridRecommender.__new__(HybridRecommender)
    rec._diversity_lambda = 0.5  # Strong diversity preference

    ranked = [(1, 0.95), (2, 0.90), (3, 0.85), (4, 0.80)]
    genres_map = {
        1: ["Action"],
        2: ["Action"],  # Same genre as 1
        3: ["Comedy"],  # Different
        4: ["Drama"],  # Different
    }

    result = rec._mmr_rerank(ranked, genres_map, top_k=4)
    result_ids = [mid for mid, _ in result]

    # First pick should be highest score (Action)
    assert result_ids[0] == 1
    # Second pick: MMR should prefer Comedy/Drama over another Action
    assert result_ids[1] in (3, 4)


def test_mmr_rerank_empty():
    rec = HybridRecommender.__new__(HybridRecommender)
    rec._diversity_lambda = 0.7
    assert rec._mmr_rerank([], {}, top_k=5) == []


def test_mmr_rerank_respects_top_k():
    rec = HybridRecommender.__new__(HybridRecommender)
    rec._diversity_lambda = 0.7

    ranked = [(1, 0.9), (2, 0.8), (3, 0.7)]
    genres_map = {1: ["Action"], 2: ["Comedy"], 3: ["Drama"]}

    result = rec._mmr_rerank(ranked, genres_map, top_k=2)
    assert len(result) == 2


# ------------------------------------------------------------------
# Jaccard similarity test
# ------------------------------------------------------------------


def test_jaccard_similarity():
    assert HybridRecommender._jaccard({"Action", "Drama"}, {"Action", "Comedy"}) == pytest.approx(
        1 / 3
    )
    assert HybridRecommender._jaccard({"Action"}, {"Action"}) == 1.0
    assert HybridRecommender._jaccard({"Action"}, {"Comedy"}) == 0.0
    assert HybridRecommender._jaccard(set(), set()) == 1.0


# ------------------------------------------------------------------
# LLM re-ranking integration test
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_with_llm_rerank(content_recommender, collab_recommender, mock_db_session):
    """When LLM reranking is enabled and succeeds, use LLM ordering."""
    mock_llm = AsyncMock()
    mock_llm.rerank_candidates.return_value = [103, 102]

    rec = HybridRecommender(
        content_recommender,
        collab_recommender,
        alpha=0.5,
        llm_service=mock_llm,
        sequel_penalty=0.5,
        diversity_lambda=0.7,
        rerank_candidates=50,
        llm_rerank_enabled=True,
    )

    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(rec._content, "get_similar_movies", new_callable=AsyncMock) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]

        results = await rec.recommend(user_id=1, db=mock_db_session, top_k=5, strategy="hybrid")

    assert len(results) > 0
    mock_llm.rerank_candidates.assert_called_once()


@pytest.mark.asyncio
async def test_hybrid_llm_failure_falls_back_to_mmr(
    content_recommender, collab_recommender, mock_db_session
):
    """When LLM reranking fails, fall back to MMR."""
    mock_llm = AsyncMock()
    mock_llm.rerank_candidates.side_effect = Exception("Ollama down")

    rec = HybridRecommender(
        content_recommender,
        collab_recommender,
        alpha=0.5,
        llm_service=mock_llm,
        sequel_penalty=0.5,
        diversity_lambda=0.7,
        rerank_candidates=50,
        llm_rerank_enabled=True,
    )

    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(rec._content, "get_similar_movies", new_callable=AsyncMock) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]

        # Should not raise — falls back to MMR
        results = await rec.recommend(user_id=1, db=mock_db_session, top_k=5, strategy="hybrid")

    assert len(results) > 0
