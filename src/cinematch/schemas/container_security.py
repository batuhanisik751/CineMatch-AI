"""Container security status schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ContainerRuntimeInfo(BaseModel):
    running_as_root: bool
    current_uid: int
    current_gid: int
    current_user: str


class FilesystemStatus(BaseModel):
    root_writable: bool
    tmp_writable: bool


class ImageInfo(BaseModel):
    base_image: str
    python_version: str
    multi_stage_build: bool


class ContainerSecurityCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class ContainerSecurityResponse(BaseModel):
    runtime: ContainerRuntimeInfo
    filesystem: FilesystemStatus
    image: ImageInfo
    checks: list[ContainerSecurityCheck]
    all_passed: bool
    checked_at: datetime
