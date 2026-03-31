"""Recommendation cache ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from cinematch.db.base import Base


class RecommendationCache(Base):
    __tablename__ = "recommendations_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    strategy: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", "strategy", name="uq_user_movie_strategy"),
        Index("idx_recs_cache_user_strategy", "user_id", "strategy"),
    )

    def __repr__(self) -> str:
        return (
            f"<RecommendationCache(user={self.user_id}, "
            f"movie={self.movie_id}, strategy='{self.strategy}')>"
        )
