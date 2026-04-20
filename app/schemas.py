from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MemoryBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    source_model: str | None = Field(default=None, max_length=64)
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)
    pinned: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for t in value:
            tag = t.strip().lower()
            if tag and tag not in cleaned:
                cleaned.append(tag)
        return cleaned


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
    source_model: str | None = Field(default=None, max_length=64)
    tags: list[str] | None = None
    importance: int | None = Field(default=None, ge=1, le=5)
    pinned: bool | None = None
    metadata: dict[str, Any] | None = None


class MemoryRead(BaseModel):
    id: str
    title: str
    body: str
    source_model: str | None
    tags: list[str]
    importance: int
    pinned: bool
    metadata: dict[str, Any]
    created_at: dt.datetime
    updated_at: dt.datetime


class MemoryListResponse(BaseModel):
    items: list[MemoryRead]
    total: int


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=lambda: ["read", "write", "files"])
    source_hint: str | None = Field(default=None, max_length=64)


class APIKeyRead(BaseModel):
    id: str
    name: str
    scopes: list[str]
    source_hint: str | None
    is_active: bool
    created_at: dt.datetime
    last_used_at: dt.datetime | None


class APIKeyCreateResponse(BaseModel):
    key: str
    details: APIKeyRead


class PullProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    required_tags: list[str] = Field(default_factory=list)
    preferred_sources: list[str] = Field(default_factory=list)
    max_items: int = Field(default=20, ge=1, le=100)
    include_pinned: bool = True
    lookback_days: int = Field(default=14, ge=1, le=3650)


class PullProfileRead(BaseModel):
    name: str
    description: str | None
    required_tags: list[str]
    preferred_sources: list[str]
    max_items: int
    include_pinned: bool
    lookback_days: int


class ContextPullResponse(BaseModel):
    generated_at: dt.datetime
    profile: PullProfileRead
    items: list[MemoryRead]


class FileAssetRead(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    description: str | None
    uploaded_at: dt.datetime


class FileShareCreate(BaseModel):
    expires_in_hours: int | None = Field(default=None, ge=1)
    max_downloads: int | None = Field(default=None, ge=1)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    note: str | None = Field(default=None, max_length=255)


class FileShareRead(BaseModel):
    id: str
    url: str
    expires_at: dt.datetime | None
    max_downloads: int | None
    download_count: int
    is_active: bool
    created_at: dt.datetime


class BulkMemoryImportItem(BaseModel):
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    source_model: str | None = None
    importance: int = Field(default=3, ge=1, le=5)
    pinned: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
