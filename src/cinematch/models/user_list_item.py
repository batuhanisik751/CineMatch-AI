"""UserListItem model — movies within a user list, with ordering."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cinematch.db.base import Base


class UserListItem(Base):
    __tablename__ = "user_list_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    list_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("list_id", "movie_id", name="uq_list_item_list_movie"),
    )

    def __repr__(self) -> str:
        return f"<UserListItem(list={self.list_id}, movie={self.movie_id}, pos={self.position})>"
