import datetime as dt
import uuid
from typing import Optional

from sqlalchemy import (
    Column,
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


memory_tags = Table(
    "memory_tags",
    Base.metadata,
    Column("memory_id", String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scopes_csv: Mapped[str] = mapped_column(String(255), default="read,write,files", nullable=False)
    source_hint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    tags: Mapped[list[Tag]] = relationship("Tag", secondary=memory_tags, lazy="joined")


class FileAsset(Base):
    __tablename__ = "file_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    shares: Mapped[list["FileShareLink"]] = relationship(
        "FileShareLink",
        back_populates="file",
        cascade="all, delete-orphan",
    )


class FileShareLink(Base):
    __tablename__ = "file_share_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("file_assets.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    max_downloads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    file: Mapped["FileAsset"] = relationship("FileAsset", back_populates="shares")


class MemoryPullProfile(Base):
    __tablename__ = "memory_pull_profiles"
    __table_args__ = (UniqueConstraint("name", name="uq_profile_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    required_tags_csv: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    preferred_sources_csv: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    max_items: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    include_pinned: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
