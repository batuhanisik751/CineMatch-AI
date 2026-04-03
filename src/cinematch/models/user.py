"""User ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from cinematch.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movielens_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(128), nullable=True)
    username: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
