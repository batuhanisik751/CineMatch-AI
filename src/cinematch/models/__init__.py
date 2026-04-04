"""SQLAlchemy ORM models — re-export all for Alembic discovery."""

from cinematch.models.audit_log import AuditLog
from cinematch.models.dismissal import Dismissal
from cinematch.models.movie import Movie
from cinematch.models.rating import Rating
from cinematch.models.recommendation import RecommendationCache
from cinematch.models.user import User
from cinematch.models.user_list import UserList
from cinematch.models.user_list_item import UserListItem
from cinematch.models.watchlist import WatchlistItem

__all__ = [
    "AuditLog",
    "Dismissal",
    "Movie",
    "Rating",
    "RecommendationCache",
    "User",
    "UserList",
    "UserListItem",
    "WatchlistItem",
]
