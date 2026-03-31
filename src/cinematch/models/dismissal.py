"""Dismissal ORM model for 'Not Interested' feedback."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cinematch.db.base import Base


class Dismissal(Base):
    __tablename__ = "dismissals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_dismissal_user_movie"),)

    def __repr__(self) -> str:
        return f"<Dismissal(user={self.user_id}, movie={self.movie_id})>"
