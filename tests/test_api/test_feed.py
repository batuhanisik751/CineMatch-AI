"""Tests for the personalized feed API endpoint."""

from __future__ import annotations

from cinematch.schemas.user import FeedResponse, FeedSection


async def test_feed_endpoint_200(client, mock_feed_service):
    """Feed endpoint returns personalized sections."""
    resp = await client.get("/api/v1/users/1/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["is_personalized"] is True
    assert len(data["sections"]) == 5
    assert data["sections"][0]["key"] == "because_you_rated"
    assert data["sections"][0]["title"] == "Because you rated The Matrix highly"
    assert len(data["sections"][0]["movies"]) == 1
    mock_feed_service.generate_feed.assert_called_once()


async def test_feed_endpoint_sections_param(client, mock_feed_service):
    """Sections query parameter is passed through to service."""
    resp = await client.get("/api/v1/users/1/feed?sections=3")
    assert resp.status_code == 200
    call_args = mock_feed_service.generate_feed.call_args
    assert call_args.kwargs.get("sections") == 3 or (
        len(call_args.args) >= 3 and call_args.args[2] == 3
    )


async def test_feed_endpoint_cached(client, mock_feed_service, mock_cache_service):
    """Feed returns cached response when available."""
    cached_response = FeedResponse(
        user_id=1,
        is_personalized=False,
        sections=[
            FeedSection(key="trending", title="Trending Now", movies=[]),
        ],
    )
    mock_cache_service.get.return_value = cached_response.model_dump_json()

    resp = await client.get("/api/v1/users/1/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_personalized"] is False
    assert len(data["sections"]) == 1
    assert data["sections"][0]["key"] == "trending"
    mock_feed_service.generate_feed.assert_not_called()


async def test_feed_endpoint_cold_start(client, mock_feed_service):
    """Cold-start user gets non-personalized feed."""
    mock_feed_service.generate_feed.return_value = FeedResponse(
        user_id=1,
        is_personalized=False,
        sections=[
            FeedSection(key="trending", title="Trending Now", movies=[]),
            FeedSection(key="top_rated", title="Top Rated", movies=[]),
            FeedSection(key="hidden_gems", title="Hidden Gems", movies=[]),
        ],
    )
    resp = await client.get("/api/v1/users/1/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_personalized"] is False
    assert len(data["sections"]) == 3
