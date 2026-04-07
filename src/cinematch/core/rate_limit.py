"""Redis-backed rate limiting via slowapi."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from cinematch.config import get_settings


def get_user_or_ip(request: Request) -> str:
    """Extract user ID from JWT for per-user rate limiting, fall back to IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            from cinematch.services.auth_service import decode_access_token

            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return get_remote_address(request)


settings = get_settings()

# Use in-memory storage when Redis is unavailable (e.g. Vercel deployment
# where Render's internal Redis is not reachable).
_storage_uri = settings.redis_url.get_secret_value()
try:
    import redis

    redis.from_url(_storage_uri).ping()
except Exception:
    _storage_uri = "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    storage_uri=_storage_uri,
    enabled=settings.rate_limit_enabled,
)
