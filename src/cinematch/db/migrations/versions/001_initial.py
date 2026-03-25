"""Initial schema: extensions, tables, and indexes.

Revision ID: 001_initial
Revises: None
Create Date: 2026-03-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions MUST be created before any table that uses their types
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # --- movies table ---
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tmdb_id", sa.Integer(), unique=True, nullable=False),
        sa.Column("imdb_id", sa.String(15), nullable=True),
        sa.Column("movielens_id", sa.Integer(), unique=True, nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("genres", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("keywords", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("cast_names", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("director", sa.String(255), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("vote_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("popularity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("poster_path", sa.String(255), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("idx_movies_tmdb_id", "movies", ["tmdb_id"])
    op.create_index("idx_movies_movielens_id", "movies", ["movielens_id"])
    op.create_index("idx_movies_imdb_id", "movies", ["imdb_id"])
    op.create_index("idx_movies_genres", "movies", ["genres"], postgresql_using="gin")
    op.create_index(
        "idx_movies_title_trgm",
        "movies",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    # NOTE: IVFFlat vector index is NOT created here.
    # It must be created AFTER bulk data load for optimal list distribution.
    # See scripts/seed_db.py for post-load index creation.

    # --- users table ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movielens_id", sa.Integer(), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("idx_users_movielens_id", "users", ["movielens_id"])

    # --- ratings table ---
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "movie_id", name="uq_user_movie"),
        sa.CheckConstraint("rating >= 0.5 AND rating <= 5.0", name="ck_rating_range"),
    )

    op.create_index("idx_ratings_user_id", "ratings", ["user_id"])
    op.create_index("idx_ratings_movie_id", "ratings", ["movie_id"])
    op.create_index("idx_ratings_timestamp", "ratings", ["timestamp"])

    # --- recommendations_cache table ---
    op.create_table(
        "recommendations_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("strategy", sa.String(20), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "movie_id", "strategy", name="uq_user_movie_strategy"),
    )

    op.create_index("idx_recs_cache_user_strategy", "recommendations_cache", ["user_id", "strategy"])


def downgrade() -> None:
    op.drop_table("recommendations_cache")
    op.drop_table("ratings")
    op.drop_table("users")
    op.drop_table("movies")
    # Do NOT drop extensions in downgrade — other schemas may use them
