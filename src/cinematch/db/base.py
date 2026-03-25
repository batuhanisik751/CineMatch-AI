"""SQLAlchemy declarative base with pgvector type support."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
