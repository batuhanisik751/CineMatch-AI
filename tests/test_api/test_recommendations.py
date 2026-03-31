"""Tests for recommendation API endpoints."""

from __future__ import annotations

from cinematch.api.deps import get_llm_service


async def test_get_recommendations_success(client, sample_movie, mock_movie_service):
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["strategy"] == "hybrid"
    assert len(data["recommendations"]) > 0
    assert "score" in data["recommendations"][0]
    assert "movie" in data["recommendations"][0]


async def test_get_recommendations_content_strategy(client, mock_hybrid_recommender):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"strategy": "content"},
    )
    assert resp.status_code == 200
    mock_hybrid_recommender.recommend.assert_called_once()
    call_kwargs = mock_hybrid_recommender.recommend.call_args
    assert call_kwargs.kwargs.get("strategy") == "content"


async def test_get_recommendations_collab_strategy(client, mock_hybrid_recommender):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"strategy": "collab"},
    )
    assert resp.status_code == 200


async def test_get_recommendations_invalid_strategy(client):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"strategy": "invalid"},
    )
    assert resp.status_code == 422


async def test_get_recommendations_with_top_k(client, mock_hybrid_recommender):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"top_k": 5},
    )
    assert resp.status_code == 200
    mock_hybrid_recommender.recommend.assert_called_once()


async def test_get_recommendations_empty_results(
    client, mock_hybrid_recommender, mock_movie_service
):
    mock_hybrid_recommender.recommend.return_value = []
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendations"] == []


async def test_get_recommendations_service_unavailable(app, client):
    from cinematch.api.deps import get_hybrid_recommender

    app.dependency_overrides[get_hybrid_recommender] = lambda: None
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 503
    assert "Recommendation service" in resp.json()["detail"]


async def test_get_recommendations_default_diversity(client, sample_movie, mock_movie_service):
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["diversity"] == "medium"


async def test_get_recommendations_with_diversity_low(client, mock_hybrid_recommender):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"diversity": "low"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["diversity"] == "low"
    call_kwargs = mock_hybrid_recommender.recommend.call_args
    assert call_kwargs.kwargs.get("diversity_lambda") == 0.9


async def test_get_recommendations_with_diversity_high(client, mock_hybrid_recommender):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"diversity": "high"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["diversity"] == "high"
    call_kwargs = mock_hybrid_recommender.recommend.call_args
    assert call_kwargs.kwargs.get("diversity_lambda") == 0.4


async def test_get_recommendations_invalid_diversity(client):
    resp = await client.get(
        "/api/v1/users/1/recommendations",
        params={"diversity": "extreme"},
    )
    assert resp.status_code == 422


async def test_get_recommendations_collab_cold_start(client, mock_hybrid_recommender):
    mock_hybrid_recommender.recommend.side_effect = ValueError(
        "User 999 has no collaborative filtering data yet."
    )
    resp = await client.get("/api/v1/users/999/recommendations", params={"strategy": "collab"})
    assert resp.status_code == 400
    assert "collaborative filtering data" in resp.json()["detail"]


# --- Explain endpoint tests ---


async def test_explain_recommendation_success(client, mock_llm_service):
    resp = await client.get("/api/v1/users/1/recommendations/explain/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["movie_id"] == 1
    assert data["title"] == "The Matrix"
    assert "explanation" in data
    assert data["score"] == 0.0
    mock_llm_service.explain_recommendation.assert_called_once()


async def test_explain_recommendation_llm_disabled(app, client):
    app.dependency_overrides[get_llm_service] = lambda: None
    resp = await client.get("/api/v1/users/1/recommendations/explain/1")
    assert resp.status_code == 503
    assert "LLM service" in resp.json()["detail"]


async def test_explain_recommendation_movie_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.get("/api/v1/users/1/recommendations/explain/999")
    assert resp.status_code == 404
    assert "Movie" in resp.json()["detail"]


async def test_explain_recommendation_no_user_ratings(client, mock_rating_service):
    mock_rating_service.get_user_ratings.return_value = ([], 0)
    resp = await client.get("/api/v1/users/1/recommendations/explain/1")
    assert resp.status_code == 404
    assert "User" in resp.json()["detail"]


async def test_explain_recommendation_with_score_param(client, mock_llm_service):
    resp = await client.get("/api/v1/users/1/recommendations/explain/1", params={"score": 0.85})
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 0.85


# --- Mood recommendations endpoint tests ---


async def test_mood_recommendations_success(client, mock_hybrid_recommender, mock_movie_service):
    resp = await client.post(
        "/api/v1/recommendations/mood",
        json={"mood": "dark gritty crime drama", "user_id": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["mood"] == "dark gritty crime drama"
    assert data["is_personalized"] is True
    assert data["alpha"] == 0.3
    assert len(data["results"]) > 0
    assert "movie" in data["results"][0]
    assert "similarity" in data["results"][0]
    mock_hybrid_recommender.mood_recommend.assert_called_once()


async def test_mood_recommendations_cold_start(client, mock_hybrid_recommender, mock_movie_service):
    mock_hybrid_recommender.mood_recommend.return_value = ([(1, 0.8)], False)
    resp = await client.post(
        "/api/v1/recommendations/mood",
        json={"mood": "feel-good comedy", "user_id": 999},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_personalized"] is False


async def test_mood_recommendations_missing_mood(client):
    resp = await client.post(
        "/api/v1/recommendations/mood",
        json={"user_id": 1},
    )
    assert resp.status_code == 422


async def test_mood_recommendations_empty_mood(client):
    resp = await client.post(
        "/api/v1/recommendations/mood",
        json={"mood": "", "user_id": 1},
    )
    assert resp.status_code == 422


async def test_mood_recommendations_alpha_out_of_range(client):
    resp = await client.post(
        "/api/v1/recommendations/mood",
        json={"mood": "thriller", "user_id": 1, "alpha": 1.5},
    )
    assert resp.status_code == 422


async def test_mood_recommendations_service_unavailable(app, client):
    from cinematch.api.deps import get_hybrid_recommender

    app.dependency_overrides[get_hybrid_recommender] = lambda: None
    resp = await client.post(
        "/api/v1/recommendations/mood",
        json={"mood": "thriller", "user_id": 1},
    )
    assert resp.status_code == 503
    assert "Recommendation service" in resp.json()["detail"]


async def test_mood_recommendations_with_custom_alpha(
    client, mock_hybrid_recommender, mock_movie_service
):
    resp = await client.post(
        "/api/v1/recommendations/mood",
        json={"mood": "epic adventure", "user_id": 1, "alpha": 0.7, "limit": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["alpha"] == 0.7
    call_kwargs = mock_hybrid_recommender.mood_recommend.call_args
    assert call_kwargs.kwargs.get("alpha") == 0.7
    assert call_kwargs.kwargs.get("top_k") == 10


async def test_mood_recommendations_cache_hit(client, mock_hybrid_recommender, mock_cache_service):
    cached_response = (
        '{"user_id":1,"mood":"thriller","alpha":0.3,"is_personalized":true,"results":[],"total":0}'
    )
    mock_cache_service.get.return_value = cached_response
    resp = await client.post(
        "/api/v1/recommendations/mood",
        json={"mood": "thriller", "user_id": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mood"] == "thriller"
    # Should NOT call mood_recommend since cache hit
    mock_hybrid_recommender.mood_recommend.assert_not_called()


# --- Smart explanation fields tests ---


async def test_get_recommendations_includes_explanation_fields(
    client, sample_movie, mock_movie_service
):
    """Response should include because_you_liked, feature_explanations, score_breakdown."""
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    rec = data["recommendations"][0]

    # because_you_liked
    assert "because_you_liked" in rec
    assert rec["because_you_liked"]["movie_id"] == 10
    assert rec["because_you_liked"]["title"] == "Inception"
    assert rec["because_you_liked"]["your_rating"] == 9.0

    # feature_explanations
    assert "feature_explanations" in rec
    assert len(rec["feature_explanations"]) > 0

    # score_breakdown
    assert "score_breakdown" in rec
    assert rec["score_breakdown"]["content_score"] == 0.8
    assert rec["score_breakdown"]["collab_score"] == 0.7
    assert rec["score_breakdown"]["alpha"] == 0.5


async def test_get_recommendations_populates_content_collab_from_breakdown(
    client, sample_movie, mock_movie_service
):
    """content_score and collab_score at top level should be populated from breakdown."""
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    rec = data["recommendations"][0]

    assert rec["content_score"] == 0.8
    assert rec["collab_score"] == 0.7


async def test_get_recommendations_null_explanation_for_no_seed(
    client, sample_movie, mock_movie_service
):
    """Recommendation without seed influence should have null because_you_liked."""
    resp = await client.get("/api/v1/users/1/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    # Second recommendation has no because_you_liked
    if len(data["recommendations"]) > 1:
        rec2 = data["recommendations"][1]
        assert rec2["because_you_liked"] is None
        assert rec2["feature_explanations"] == []


# --- From-seed recommendations endpoint tests ---


async def test_from_seed_recommendations_success(
    client, mock_hybrid_recommender, mock_movie_service
):
    resp = await client.get("/api/v1/users/1/recommendations/from-seed/5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["strategy"] == "from-seed"
    assert "seed_movie" in data
    assert data["seed_movie"]["id"] == 1  # from mock_movie_service.get_by_id
    assert len(data["recommendations"]) > 0
    rec = data["recommendations"][0]
    assert "score" in rec
    assert "movie" in rec
    assert rec["because_you_liked"]["title"] == "The Matrix"
    mock_hybrid_recommender.from_seed_recommend.assert_called_once()


async def test_from_seed_recommendations_movie_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.get("/api/v1/users/1/recommendations/from-seed/999")
    assert resp.status_code == 404
    assert "Movie" in resp.json()["detail"]


async def test_from_seed_recommendations_service_unavailable(app, client):
    from cinematch.api.deps import get_hybrid_recommender

    app.dependency_overrides[get_hybrid_recommender] = lambda: None
    resp = await client.get("/api/v1/users/1/recommendations/from-seed/5")
    assert resp.status_code == 503
    assert "Recommendation service" in resp.json()["detail"]


async def test_from_seed_recommendations_empty_results(
    client, mock_hybrid_recommender, mock_movie_service
):
    mock_hybrid_recommender.from_seed_recommend.return_value = []
    resp = await client.get("/api/v1/users/1/recommendations/from-seed/5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendations"] == []
    assert data["seed_movie"]["id"] == 1


async def test_from_seed_recommendations_with_limit(client, mock_hybrid_recommender):
    resp = await client.get("/api/v1/users/1/recommendations/from-seed/5?limit=10")
    assert resp.status_code == 200
    call_kwargs = mock_hybrid_recommender.from_seed_recommend.call_args
    assert call_kwargs.kwargs.get("top_k") == 10
