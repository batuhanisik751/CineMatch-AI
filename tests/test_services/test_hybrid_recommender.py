"""Tests for HybridRecommender."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cinematch.services.hybrid_recommender import HybridRecommender, RecommendationResult


def _db_execute_factory(
    top_rated: list[tuple] | None = None,
    rated_ids: list[tuple] | None = None,
    titles: list[tuple] | None = None,
    genres: list[tuple] | None = None,
    metadata: list[tuple] | None = None,
):
    """Build a query-matching side_effect for mock db.execute calls.

    Uses query string inspection to return the right mock data regardless
    of call ordering (which varies depending on LLM rerank path).
    """
    if top_rated is None:
        top_rated = [(101, 10, ["Action", "Sci-Fi"])]
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
    if metadata is None:
        metadata = [
            (101, ["Action", "Sci-Fi"], "Director A", ["Actor X"]),
            (102, ["Action"], "Director A", ["Actor X"]),
            (103, ["Comedy"], "Director B", ["Actor Y"]),
            (104, ["Drama"], "Director C", ["Actor Z"]),
            (105, ["Sci-Fi"], "Director D", ["Actor X"]),
        ]

    def _make_result(data):
        r = MagicMock()
        r.fetchall.return_value = data
        return r

    title_call_count = 0

    async def _side_effect(query, params=None):
        nonlocal title_call_count
        q = str(query)
        if "r.movie_id, r.rating, m.genres" in q:
            return _make_result(top_rated)
        if "SELECT movie_id FROM ratings" in q:
            return _make_result(rated_ids)
        if "SELECT id, title FROM movies" in q:
            title_call_count += 1
            if title_call_count == 1:
                return _make_result([(101, "Movie A")] + titles)
            return _make_result(titles)
        if "SELECT id, genres, director, cast_names" in q:
            return _make_result(metadata)
        if "SELECT id, genres FROM movies" in q:
            return _make_result(genres)
        if "SELECT movie_id, rating FROM ratings" in q:
            return _make_result(top_rated)
        return _make_result([])

    return _side_effect


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
    result_ids = [r.movie_id for r in results]
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
    assert all(isinstance(r, RecommendationResult) for r in results)


@pytest.mark.asyncio
async def test_hybrid_recommend_excludes_already_rated(hybrid_recommender, mock_db_session):
    mock_db_session.execute = AsyncMock(
        side_effect=_db_execute_factory(
            top_rated=[(101, 10, ["Action"]), (102, 8, ["Drama"])],
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

    result_ids = [r.movie_id for r in results]
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
    result_ids = [r.movie_id for r in results]
    assert result_ids == [101, 103, 105]
    # Collab-only should have alpha=0.0 and no seed influence
    for r in results:
        assert r.score_breakdown is not None
        assert r.score_breakdown.alpha == 0.0
        assert r.score_breakdown.content_score == 0.0
        assert r.because_you_liked is None


@pytest.mark.asyncio
async def test_collab_strategy_cold_start_raises_error(hybrid_recommender, mock_db_session):
    with pytest.raises(ValueError, match="no collaborative filtering data"):
        await hybrid_recommender.recommend(
            user_id=999, db=mock_db_session, top_k=5, strategy="collab"
        )


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


# ------------------------------------------------------------------
# Mood-based recommendation tests
# ------------------------------------------------------------------


def _mood_db_execute_factory(
    top_rated: list[tuple] | None = None,
    rated_ids: list[tuple] | None = None,
):
    """Build side_effect for mood_recommend db.execute calls.

    Mood recommend calls db.execute in this order:
    1. _get_user_top_rated_diverse
    2. _get_user_rated_movie_ids
    """
    if top_rated is None:
        top_rated = [(101, 9, ["Action", "Sci-Fi"]), (102, 8, ["Drama"])]
    if rated_ids is None:
        rated_ids = [(101,), (102,)]

    def _make_result(data):
        r = MagicMock()
        r.fetchall.return_value = data
        return r

    return [
        _make_result(top_rated),
        _make_result(rated_ids),
    ]


@pytest.mark.asyncio
async def test_mood_recommend_cold_start(hybrid_recommender, mock_db_session):
    """User with no ratings gets pure mood results, is_personalized=False."""
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []

    # First call: top_rated (empty), second call: rated_ids (empty)
    mock_db_session.execute = AsyncMock(side_effect=[empty_result, empty_result])

    results, is_personalized = await hybrid_recommender.mood_recommend(
        mood_text="dark gritty crime drama",
        user_id=999,
        db=mock_db_session,
        alpha=0.3,
        top_k=3,
    )

    assert not is_personalized
    assert len(results) > 0
    for mid, score in results:
        assert isinstance(mid, int)
        assert isinstance(score, float)


@pytest.mark.asyncio
async def test_mood_recommend_with_ratings(hybrid_recommender, mock_db_session):
    """User with ratings gets personalized results, is_personalized=True."""
    mock_db_session.execute = AsyncMock(side_effect=_mood_db_execute_factory())

    results, is_personalized = await hybrid_recommender.mood_recommend(
        mood_text="heartwarming feel-good comedy",
        user_id=1,
        db=mock_db_session,
        alpha=0.3,
        top_k=3,
    )

    assert is_personalized
    assert len(results) > 0
    # Should exclude already-rated movies
    result_ids = {mid for mid, _ in results}
    assert 101 not in result_ids
    assert 102 not in result_ids


@pytest.mark.asyncio
async def test_mood_recommend_alpha_zero_is_pure_mood(hybrid_recommender, mock_db_session):
    """alpha=0 should produce results based purely on mood, not user taste."""
    mock_db_session.execute = AsyncMock(side_effect=_mood_db_execute_factory())

    results_alpha0, is_p = await hybrid_recommender.mood_recommend(
        mood_text="suspenseful thriller", user_id=1, db=mock_db_session, alpha=0.0, top_k=3
    )

    assert is_p  # Still True because user has ratings (blending just weights mood 100%)
    assert len(results_alpha0) > 0


@pytest.mark.asyncio
async def test_mood_recommend_alpha_one_is_pure_taste(hybrid_recommender, mock_db_session):
    """alpha=1 should produce results based purely on user taste, ignoring mood."""
    mock_db_session.execute = AsyncMock(side_effect=_mood_db_execute_factory())

    results, is_p = await hybrid_recommender.mood_recommend(
        mood_text="any text ignored", user_id=1, db=mock_db_session, alpha=1.0, top_k=3
    )

    assert is_p
    assert len(results) > 0


@pytest.mark.asyncio
async def test_mood_recommend_excludes_rated_movies(hybrid_recommender, mock_db_session):
    """Mood results should never include movies the user has already rated."""
    mock_db_session.execute = AsyncMock(
        side_effect=_mood_db_execute_factory(
            rated_ids=[(101,), (102,), (103,)],
        )
    )

    results, _ = await hybrid_recommender.mood_recommend(
        mood_text="epic adventure", user_id=1, db=mock_db_session, top_k=5
    )

    result_ids = {mid for mid, _ in results}
    assert result_ids.isdisjoint({101, 102, 103})


# ------------------------------------------------------------------
# Smart Recommendation Explanation tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_recommend_returns_recommendation_results(hybrid_recommender, mock_db_session):
    """All results should be RecommendationResult instances."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]
        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    assert all(isinstance(r, RecommendationResult) for r in results)


@pytest.mark.asyncio
async def test_hybrid_recommend_includes_score_breakdown(hybrid_recommender, mock_db_session):
    """Hybrid strategy should populate score_breakdown with alpha=0.5."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]
        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    assert len(results) > 0
    for r in results:
        assert r.score_breakdown is not None
        assert r.score_breakdown.alpha == 0.5
        assert 0.0 <= r.score_breakdown.content_score <= 1.0
        assert 0.0 <= r.score_breakdown.collab_score <= 1.0


@pytest.mark.asyncio
async def test_hybrid_recommend_includes_because_you_liked(hybrid_recommender, mock_db_session):
    """Results from content scoring should have because_you_liked set."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]
        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    # At least some results should have because_you_liked (those from content scoring)
    content_explained = [r for r in results if r.because_you_liked is not None]
    assert len(content_explained) > 0
    for r in content_explained:
        assert r.because_you_liked.movie_id == 101  # the seed movie
        assert r.because_you_liked.your_rating == 10.0
        assert r.because_you_liked.title == "Movie A"


@pytest.mark.asyncio
async def test_content_only_has_alpha_one_breakdown(hybrid_recommender, mock_db_session):
    """Content-only strategy should have alpha=1.0 and collab_score=0.0."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]
        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="content"
        )

    assert len(results) > 0
    for r in results:
        assert r.score_breakdown is not None
        assert r.score_breakdown.alpha == 1.0
        assert r.score_breakdown.collab_score == 0.0


@pytest.mark.asyncio
async def test_feature_explanation_director_match(hybrid_recommender, mock_db_session):
    """When seed and candidate share a director, an explanation should appear."""
    # Seed movie 101 has Director A; candidate 102 also has Director A
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]
        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    movie_102 = next((r for r in results if r.movie_id == 102), None)
    if movie_102 is not None:
        director_explanations = [
            e for e in movie_102.feature_explanations if "director" in e.lower()
        ]
        assert len(director_explanations) > 0
        assert "Director A" in director_explanations[0]


# ------------------------------------------------------------------
# From-seed recommendation tests
# ------------------------------------------------------------------


def _from_seed_db_factory(
    rated_ids: list[tuple] | None = None,
    titles: list[tuple] | None = None,
    genres: list[tuple] | None = None,
    metadata: list[tuple] | None = None,
):
    """Build query-matching side_effect for from_seed_recommend db calls."""
    if rated_ids is None:
        rated_ids = [(101,)]
    if titles is None:
        titles = [(101, "Seed Movie"), (102, "Movie B"), (103, "Movie C"), (104, "Movie D")]
    if genres is None:
        genres = [(102, ["Action"]), (103, ["Comedy"]), (104, ["Drama"])]
    if metadata is None:
        metadata = [
            (101, ["Action", "Sci-Fi"], "Director A", ["Actor X"]),
            (102, ["Action"], "Director A", ["Actor X"]),
            (103, ["Comedy"], "Director B", ["Actor Y"]),
            (104, ["Drama"], "Director C", ["Actor Z"]),
        ]

    def _make_result(data):
        r = MagicMock()
        r.fetchall.return_value = data
        return r

    async def _side_effect(query, params=None):
        q = str(query)
        if "SELECT movie_id FROM ratings" in q:
            return _make_result(rated_ids)
        if "SELECT id, title FROM movies" in q:
            return _make_result(titles)
        if "SELECT id, genres, director, cast_names" in q:
            return _make_result(metadata)
        if "SELECT id, genres FROM movies" in q:
            return _make_result(genres)
        return _make_result([])

    return _side_effect


@pytest.mark.asyncio
async def test_from_seed_returns_results(hybrid_recommender, mock_db_session):
    """from_seed_recommend should return personalized results for known user."""
    mock_db_session.execute = AsyncMock(side_effect=_from_seed_db_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8), (104, 0.7)]

        results = await hybrid_recommender.from_seed_recommend(
            seed_movie_id=101,
            user_id=1,
            db=mock_db_session,
            top_k=5,
        )

    assert len(results) > 0
    assert all(isinstance(r, RecommendationResult) for r in results)
    # Seed movie (101) should not appear in results (it's excluded)
    result_ids = [r.movie_id for r in results]
    assert 101 not in result_ids


@pytest.mark.asyncio
async def test_from_seed_cold_start_user(hybrid_recommender, mock_db_session):
    """Cold-start user should get content-only results (alpha=1.0)."""
    mock_db_session.execute = AsyncMock(
        side_effect=_from_seed_db_factory(rated_ids=[]),
    )

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]

        results = await hybrid_recommender.from_seed_recommend(
            seed_movie_id=101,
            user_id=999,
            db=mock_db_session,
            top_k=5,
        )

    assert len(results) > 0
    for r in results:
        assert r.score_breakdown is not None
        assert r.score_breakdown.alpha == 1.0
        assert r.score_breakdown.collab_score == 0.0


@pytest.mark.asyncio
async def test_from_seed_excludes_rated_movies(hybrid_recommender, mock_db_session):
    """Already-rated movies should be excluded from from-seed results."""
    mock_db_session.execute = AsyncMock(
        side_effect=_from_seed_db_factory(rated_ids=[(102,), (103,)]),
    )

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.95), (103, 0.85), (104, 0.7)]

        results = await hybrid_recommender.from_seed_recommend(
            seed_movie_id=101,
            user_id=1,
            db=mock_db_session,
            top_k=5,
        )

    result_ids = [r.movie_id for r in results]
    assert 102 not in result_ids
    assert 103 not in result_ids


@pytest.mark.asyncio
async def test_from_seed_excludes_seed_movie(hybrid_recommender, mock_db_session):
    """The seed movie itself should never appear in results."""
    mock_db_session.execute = AsyncMock(
        side_effect=_from_seed_db_factory(rated_ids=[]),
    )

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        # ContentRecommender normally excludes it, but ensure our method also does
        mock_content.return_value = [(101, 0.99), (102, 0.9), (103, 0.8)]

        results = await hybrid_recommender.from_seed_recommend(
            seed_movie_id=101,
            user_id=999,
            db=mock_db_session,
            top_k=5,
        )

    result_ids = [r.movie_id for r in results]
    assert 101 not in result_ids


@pytest.mark.asyncio
async def test_from_seed_empty_similar(hybrid_recommender, mock_db_session):
    """When seed movie has no similar movies, return empty list."""
    mock_db_session.execute = AsyncMock(
        side_effect=_from_seed_db_factory(),
    )

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = []

        results = await hybrid_recommender.from_seed_recommend(
            seed_movie_id=101,
            user_id=1,
            db=mock_db_session,
            top_k=5,
        )

    assert results == []


@pytest.mark.asyncio
async def test_from_seed_because_you_liked_points_to_seed(hybrid_recommender, mock_db_session):
    """All results should have because_you_liked pointing to the seed movie."""
    mock_db_session.execute = AsyncMock(side_effect=_from_seed_db_factory())

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]

        results = await hybrid_recommender.from_seed_recommend(
            seed_movie_id=101,
            user_id=1,
            db=mock_db_session,
            top_k=5,
        )

    for r in results:
        assert r.because_you_liked is not None
        assert r.because_you_liked.movie_id == 101
        assert r.because_you_liked.title == "Seed Movie"
        assert r.because_you_liked.your_rating == 10.0


# ------------------------------------------------------------------
# watchlist_recommend
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watchlist_recommend_returns_similar_movies(hybrid_recommender, mock_db_session):
    """Watchlist recommend returns neighbours of the mean watchlist embedding."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory(rated_ids=[]))

    results = await hybrid_recommender.watchlist_recommend(
        watchlist_movie_ids=[101, 102],
        user_id=1,
        db=mock_db_session,
        top_k=3,
    )

    assert len(results) > 0
    result_ids = [mid for mid, _ in results]
    # Watchlisted movies must be excluded from results
    assert 101 not in result_ids
    assert 102 not in result_ids


@pytest.mark.asyncio
async def test_watchlist_recommend_empty_watchlist(hybrid_recommender, mock_db_session):
    """Empty watchlist returns no recommendations."""
    results = await hybrid_recommender.watchlist_recommend(
        watchlist_movie_ids=[],
        user_id=1,
        db=mock_db_session,
    )
    assert results == []


@pytest.mark.asyncio
async def test_watchlist_recommend_excludes_rated_movies(hybrid_recommender, mock_db_session):
    """Rated movies are excluded from watchlist recommendations."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory(rated_ids=[(103,), (104,)]))

    results = await hybrid_recommender.watchlist_recommend(
        watchlist_movie_ids=[101],
        user_id=1,
        db=mock_db_session,
        top_k=5,
    )

    result_ids = [mid for mid, _ in results]
    assert 103 not in result_ids
    assert 104 not in result_ids
    assert 101 not in result_ids  # watchlisted movie excluded too
