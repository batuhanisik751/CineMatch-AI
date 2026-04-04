"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.db.session import get_db
from cinematch.models.user import User
from cinematch.services.auth_service import decode_access_token

if TYPE_CHECKING:
    from cinematch.core.cache import CacheService
    from cinematch.services.achievement_service import AchievementService
    from cinematch.services.audit_service import AuditService
    from cinematch.services.bingo_service import BingoService
    from cinematch.services.blind_spot_service import BlindSpotService
    from cinematch.services.challenge_service import ChallengeService
    from cinematch.services.collab_recommender import CollabRecommender
    from cinematch.services.content_recommender import ContentRecommender
    from cinematch.services.dismissal_service import DismissalService
    from cinematch.services.embedding_service import EmbeddingService
    from cinematch.services.feed_service import FeedService
    from cinematch.services.global_stats_service import GlobalStatsService
    from cinematch.services.hybrid_recommender import HybridRecommender
    from cinematch.services.llm_service import LLMService
    from cinematch.services.movie_service import MovieService
    from cinematch.services.onboarding_service import OnboardingService
    from cinematch.services.rating_comparison_service import RatingComparisonService
    from cinematch.services.rating_service import RatingService
    from cinematch.services.rewatch_service import RewatchService
    from cinematch.services.streak_service import StreakService
    from cinematch.services.taste_evolution_service import TasteEvolutionService
    from cinematch.services.taste_profile_service import TasteProfileService
    from cinematch.services.thematic_collection_service import ThematicCollectionService
    from cinematch.services.user_list_service import UserListService
    from cinematch.services.user_stats_service import UserStatsService
    from cinematch.services.watchlist_service import WatchlistService

# Re-export get_db so routes can import from one place
__all__ = ["get_current_user", "get_db", "require_same_user"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT token and return the authenticated user."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: int | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


def require_same_user(current_user_id: int, path_user_id: int) -> None:
    """Raise 403 if the authenticated user doesn't match the path user_id."""
    if current_user_id != path_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")


def get_movie_service(request: Request) -> MovieService:
    return request.app.state.movie_service


def get_rating_service(request: Request) -> RatingService:
    return request.app.state.rating_service


def get_content_recommender(request: Request) -> ContentRecommender | None:
    return getattr(request.app.state, "content_recommender", None)


def get_hybrid_recommender(request: Request) -> HybridRecommender | None:
    return getattr(request.app.state, "hybrid_recommender", None)


def get_cache_service(request: Request) -> CacheService | None:
    return getattr(request.app.state, "cache_service", None)


def get_embedding_service(request: Request) -> EmbeddingService | None:
    return getattr(request.app.state, "embedding_service", None)


def get_llm_service(request: Request) -> LLMService | None:
    return getattr(request.app.state, "llm_service", None)


def get_user_stats_service(request: Request) -> UserStatsService:
    return request.app.state.user_stats_service


def get_watchlist_service(request: Request) -> WatchlistService:
    return request.app.state.watchlist_service


def get_dismissal_service(request: Request) -> DismissalService:
    return request.app.state.dismissal_service


def get_feed_service(request: Request) -> FeedService:
    return request.app.state.feed_service


def get_taste_profile_service(request: Request) -> TasteProfileService:
    return request.app.state.taste_profile_service


def get_rating_comparison_service(request: Request) -> RatingComparisonService:
    return request.app.state.rating_comparison_service


def get_streak_service(request: Request) -> StreakService:
    return request.app.state.streak_service


def get_taste_evolution_service(request: Request) -> TasteEvolutionService:
    return request.app.state.taste_evolution_service


def get_global_stats_service(request: Request) -> GlobalStatsService:
    return request.app.state.global_stats_service


def get_thematic_collection_service(request: Request) -> ThematicCollectionService:
    return request.app.state.thematic_collection_service


def get_user_list_service(request: Request) -> UserListService:
    return request.app.state.user_list_service


def get_achievement_service(request: Request) -> AchievementService:
    return request.app.state.achievement_service


def get_challenge_service(request: Request) -> ChallengeService:
    return request.app.state.challenge_service


def get_bingo_service(request: Request) -> BingoService:
    return request.app.state.bingo_service


def get_rewatch_service(request: Request) -> RewatchService:
    return request.app.state.rewatch_service


def get_onboarding_service(request: Request) -> OnboardingService:
    return request.app.state.onboarding_service


def get_blind_spot_service(request: Request) -> BlindSpotService:
    return request.app.state.blind_spot_service


def get_collab_recommender(request: Request) -> CollabRecommender | None:
    return getattr(request.app.state, "collab_recommender", None)


def get_audit_service(request: Request) -> AuditService:
    return request.app.state.audit_service


def get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract IP address and User-Agent from request."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua
