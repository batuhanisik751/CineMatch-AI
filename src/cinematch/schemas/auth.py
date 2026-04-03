"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Registration request body."""

    email: str = Field(..., min_length=5, max_length=320)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Login request body (JSON alternative to OAuth2 form)."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response returned after login/register."""

    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
