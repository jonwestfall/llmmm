from __future__ import annotations

import csv
import datetime as dt
import io
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import APIKey, FileAsset, FileShareLink, Memory, MemoryPullProfile, Tag
from app.schemas import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyRead,
    MemoryCreate,
    MemoryRead,
    MemoryUpdate,
    PullProfileCreate,
    PullProfileRead,
)
from app.security import generate_api_key, normalize_scopes


@dataclass
class MemoryListResult:
    items: list[MemoryRead]
    total: int


def _tag_list(csv_value: str) -> list[str]:
    return [v.strip() for v in csv_value.split(",") if v.strip()]


def _csv(values: list[str]) -> str:
    return ",".join(values)


def serialize_memory(memory: Memory) -> MemoryRead:
    return MemoryRead(
        id=memory.id,
        title=memory.title,
        body=memory.body,
        source_model=memory.source_model,
        tags=sorted([t.name for t in memory.tags]),
        importance=memory.importance,
        pinned=memory.pinned,
        metadata=memory.metadata_json or {},
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


def _get_or_create_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    if not tag_names:
        return []

    existing = db.scalars(select(Tag).where(Tag.name.in_(tag_names))).all()
    by_name = {t.name: t for t in existing}
    created: list[Tag] = []

    for name in tag_names:
        if name in by_name:
            continue
        tag = Tag(name=name)
        db.add(tag)
        created.append(tag)

    if created:
        db.flush()

    return [by_name.get(name) or next(t for t in created if t.name == name) for name in tag_names]


def create_memory(db: Session, payload: MemoryCreate) -> Memory:
    tags = _get_or_create_tags(db, payload.tags)
    memory = Memory(
        title=payload.title,
        body=payload.body,
        source_model=payload.source_model,
        importance=payload.importance,
        pinned=payload.pinned,
        metadata_json=payload.metadata,
        tags=tags,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def update_memory(db: Session, memory: Memory, payload: MemoryUpdate) -> Memory:
    if payload.title is not None:
        memory.title = payload.title
    if payload.body is not None:
        memory.body = payload.body
    if payload.source_model is not None:
        memory.source_model = payload.source_model
    if payload.importance is not None:
        memory.importance = payload.importance
    if payload.pinned is not None:
        memory.pinned = payload.pinned
    if payload.metadata is not None:
        memory.metadata_json = payload.metadata
    if payload.tags is not None:
        memory.tags = _get_or_create_tags(db, payload.tags)

    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def list_memories(
    db: Session,
    q: str | None = None,
    tags: list[str] | None = None,
    source_model: str | None = None,
    pinned: bool | None = None,
    since: dt.datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> MemoryListResult:
    stmt = select(Memory).order_by(Memory.pinned.desc(), Memory.updated_at.desc())
    count_stmt = select(func.count(Memory.id))

    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(or_(Memory.title.ilike(pattern), Memory.body.ilike(pattern)))
    if source_model:
        filters.append(Memory.source_model == source_model)
    if pinned is not None:
        filters.append(Memory.pinned.is_(pinned))
    if since:
        filters.append(Memory.updated_at >= since)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    if tags:
        for name in tags:
            stmt = stmt.where(Memory.tags.any(Tag.name == name))
            count_stmt = count_stmt.where(Memory.tags.any(Tag.name == name))

    total = db.scalar(count_stmt) or 0
    memories = db.scalars(stmt.limit(limit).offset(offset)).unique().all()
    return MemoryListResult(items=[serialize_memory(m) for m in memories], total=total)


def create_api_key_record(db: Session, payload: APIKeyCreate) -> APIKeyCreateResponse:
    key, key_hash = generate_api_key()
    scopes = normalize_scopes(payload.scopes)
    api_key = APIKey(
        name=payload.name,
        key_hash=key_hash,
        scopes_csv=_csv(scopes),
        source_hint=payload.source_hint,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyCreateResponse(
        key=key,
        details=APIKeyRead(
            id=api_key.id,
            name=api_key.name,
            scopes=scopes,
            source_hint=api_key.source_hint,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
        ),
    )


def list_api_keys(db: Session) -> list[APIKeyRead]:
    keys = db.scalars(select(APIKey).order_by(APIKey.created_at.desc())).all()
    return [
        APIKeyRead(
            id=k.id,
            name=k.name,
            scopes=_tag_list(k.scopes_csv),
            source_hint=k.source_hint,
            is_active=k.is_active,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]


def revoke_api_key(db: Session, key_id: str) -> None:
    key = db.get(APIKey, key_id)
    if key:
        key.is_active = False
        db.add(key)
        db.commit()


def create_or_update_pull_profile(db: Session, payload: PullProfileCreate) -> MemoryPullProfile:
    profile = db.scalar(select(MemoryPullProfile).where(MemoryPullProfile.name == payload.name))
    if not profile:
        profile = MemoryPullProfile(name=payload.name)

    profile.description = payload.description
    profile.required_tags_csv = _csv(payload.required_tags)
    profile.preferred_sources_csv = _csv(payload.preferred_sources)
    profile.max_items = payload.max_items
    profile.include_pinned = payload.include_pinned
    profile.lookback_days = payload.lookback_days
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_pull_profile(db: Session, name: str) -> PullProfileRead | None:
    profile = db.scalar(select(MemoryPullProfile).where(MemoryPullProfile.name == name))
    if not profile:
        return None
    return PullProfileRead(
        name=profile.name,
        description=profile.description,
        required_tags=_tag_list(profile.required_tags_csv),
        preferred_sources=_tag_list(profile.preferred_sources_csv),
        max_items=profile.max_items,
        include_pinned=profile.include_pinned,
        lookback_days=profile.lookback_days,
    )


def ensure_default_pull_profile(db: Session) -> PullProfileRead:
    profile = get_pull_profile(db, "default")
    if profile:
        return profile

    created = create_or_update_pull_profile(
        db,
        PullProfileCreate(
            name="default",
            description="Pinned + recent high-signal memories",
            required_tags=[],
            preferred_sources=[],
            max_items=20,
            include_pinned=True,
            lookback_days=30,
        ),
    )
    return PullProfileRead(
        name=created.name,
        description=created.description,
        required_tags=_tag_list(created.required_tags_csv),
        preferred_sources=_tag_list(created.preferred_sources_csv),
        max_items=created.max_items,
        include_pinned=created.include_pinned,
        lookback_days=created.lookback_days,
    )


def pull_context(db: Session, profile_name: str) -> tuple[PullProfileRead, list[MemoryRead]]:
    profile = get_pull_profile(db, profile_name) or ensure_default_pull_profile(db)

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=profile.lookback_days)
    stmt = select(Memory).where(Memory.updated_at >= since)

    if profile.required_tags:
        for tag_name in profile.required_tags:
            stmt = stmt.where(Memory.tags.any(Tag.name == tag_name))

    if profile.preferred_sources:
        stmt = stmt.where(Memory.source_model.in_(profile.preferred_sources))

    if not profile.include_pinned:
        stmt = stmt.where(Memory.pinned.is_(False))

    stmt = stmt.order_by(Memory.pinned.desc(), Memory.importance.desc(), Memory.updated_at.desc()).limit(profile.max_items)
    memories = db.scalars(stmt).unique().all()
    return profile, [serialize_memory(m) for m in memories]


def memories_to_jsonl(memories: list[MemoryRead]) -> str:
    lines: list[str] = []
    for m in memories:
        lines.append(m.model_dump_json())
    return "\n".join(lines)


def memories_to_csv(memories: list[MemoryRead]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "title", "body", "source_model", "tags", "importance", "pinned", "created_at", "updated_at"])
    for m in memories:
        writer.writerow(
            [
                m.id,
                m.title,
                m.body,
                m.source_model or "",
                ",".join(m.tags),
                m.importance,
                m.pinned,
                m.created_at.isoformat(),
                m.updated_at.isoformat(),
            ]
        )
    return buffer.getvalue()
