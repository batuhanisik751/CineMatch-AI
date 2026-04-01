"""Movie ORM model."""

from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from cinematch.db.base import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    imdb_id: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    movielens_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    genres: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    cast_names: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    director: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    vote_average: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    popularity: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    embedding = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_movies_genres", "genres", postgresql_using="gin"),
        Index("idx_movies_cast_names", "cast_names", postgresql_using="gin"),
        Index("idx_movies_keywords", "keywords", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Movie(id={self.id}, title='{self.title}')>"
