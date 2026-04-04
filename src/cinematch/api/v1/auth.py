"""Authentication endpoints: register, login, and current user info."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_audit_service, get_client_info, get_current_user, get_db
from cinematch.config import get_settings
from cinematch.core.rate_limit import limiter
from cinematch.models.user import User
from cinematch.schemas.auth import RegisterRequest, TokenResponse
from cinematch.schemas.user import UserResponse
from cinematch.services.audit_service import AuditService
from cinematch.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_user_by_email,
    get_user_by_username,
    register_user,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit(get_settings().rate_limit_auth)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> TokenResponse:
    """Register a new user account and return a JWT token."""
    ip, ua = get_client_info(request)
    email = body.email.lower().strip()

    if await get_user_by_email(email, db):
        raise HTTPException(status_code=409, detail="Email already registered")

    if await get_user_by_username(body.username.strip(), db):
        raise HTTPException(status_code=409, detail="Username already taken")

    user = await register_user(email, body.username, body.password, db)
    await audit.log(
        "auth.register",
        db,
        user_id=user.id,
        ip_address=ip,
        user_agent=ua,
    )
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username or "",
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(get_settings().rate_limit_auth)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> TokenResponse:
    """Authenticate with email (as username) and password. Returns a JWT token.

    Uses OAuth2 form format for Swagger UI compatibility.
    The `username` field should contain the user's email address.
    """
    ip, ua = get_client_info(request)
    user = await authenticate_user(form_data.username, form_data.password, db)
    if user is None:
        await audit.log(
            "auth.login_failed",
            db,
            detail={"email": form_data.username},
            ip_address=ip,
            user_agent=ua,
            status="failure",
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await audit.log("auth.login", db, user_id=user.id, ip_address=ip, user_agent=ua)
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username or "",
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user's info."""
    return current_user
