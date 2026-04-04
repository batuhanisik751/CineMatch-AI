"""Database connection security status schemas."""

from __future__ import annotations

from pydantic import BaseModel


class SSLStatus(BaseModel):
    configured_mode: str
    active: bool
    protocol_version: str | None


class StatementTimeoutStatus(BaseModel):
    configured_ms: int
    active: str


class ConnectionInfo(BaseModel):
    current_user: str
    current_database: str


class PoolStatus(BaseModel):
    size: int
    checked_in: int
    checked_out: int
    overflow: int
    pool_recycle: int
    pool_pre_ping: bool


class PgvectorQuerySafety(BaseModel):
    typed_bindings: bool
    affected_services: list[str]


class DbSecurityStatusResponse(BaseModel):
    ssl: SSLStatus
    statement_timeout: StatementTimeoutStatus
    connection: ConnectionInfo
    pool: PoolStatus
    pgvector_query_safety: PgvectorQuerySafety
