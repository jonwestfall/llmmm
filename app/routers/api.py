from __future__ import annotations

import datetime as dt
import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import enforce_rate_limit, require_api_scopes
from app.config import settings
from app.db import get_db
from app.models import FileAsset, FileShareLink, Memory
from app.schemas import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyRead,
    BulkMemoryImportItem,
    ContextPullResponse,
    FileAssetRead,
    FileShareCreate,
    FileShareRead,
    MemoryCreate,
    MemoryListResponse,
    MemoryRead,
    MemoryUpdate,
    PullProfileCreate,
    PullProfileRead,
)
from app.security import generate_share_token, hash_password
from app.services import (
    create_api_key_record,
    create_memory,
    create_or_update_pull_profile,
    ensure_default_pull_profile,
    list_api_keys,
    list_memories,
    memories_to_csv,
    memories_to_jsonl,
    pull_context,
    revoke_api_key,
    serialize_memory,
    update_memory,
)

router = APIRouter(prefix="/api/v1", tags=["api"])


def _memory_or_404(db: Session, memory_id: str) -> Memory:
    memory = db.get(Memory, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


def _safe_filename(name: str) -> str:
    keep = [c for c in name if c.isalnum() or c in {"-", "_", "."}]
    cleaned = "".join(keep).strip(".")
    return cleaned or "file"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@router.post("/memories", response_model=MemoryRead, dependencies=[Depends(enforce_rate_limit)])
def create_memory_endpoint(
    payload: MemoryCreate,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("write")),
):
    memory = create_memory(db, payload)
    return serialize_memory(memory)


@router.get("/memories", response_model=MemoryListResponse, dependencies=[Depends(enforce_rate_limit)])
def list_memories_endpoint(
    q: str | None = None,
    tags: list[str] = Query(default_factory=list),
    source_model: str | None = None,
    pinned: bool | None = None,
    since: dt.datetime | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("read")),
):
    result = list_memories(
        db,
        q=q,
        tags=[t.strip().lower() for t in tags if t.strip()],
        source_model=source_model,
        pinned=pinned,
        since=since,
        limit=limit,
        offset=offset,
    )
    return MemoryListResponse(items=result.items, total=result.total)


@router.get("/memories/{memory_id}", response_model=MemoryRead, dependencies=[Depends(enforce_rate_limit)])
def get_memory_endpoint(
    memory_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("read")),
):
    memory = _memory_or_404(db, memory_id)
    return serialize_memory(memory)


@router.put("/memories/{memory_id}", response_model=MemoryRead, dependencies=[Depends(enforce_rate_limit)])
def update_memory_endpoint(
    memory_id: str,
    payload: MemoryUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("write")),
):
    memory = _memory_or_404(db, memory_id)
    memory = update_memory(db, memory, payload)
    return serialize_memory(memory)


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(enforce_rate_limit)])
def delete_memory_endpoint(
    memory_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("write")),
):
    memory = _memory_or_404(db, memory_id)
    db.delete(memory)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/memories/bulk-import", response_model=MemoryListResponse, dependencies=[Depends(enforce_rate_limit)])
def bulk_import_memories(
    payload: list[BulkMemoryImportItem],
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("write")),
):
    created: list[MemoryRead] = []
    for item in payload:
        memory = create_memory(db, MemoryCreate(**item.model_dump()))
        created.append(serialize_memory(memory))
    return MemoryListResponse(items=created, total=len(created))


@router.get("/memories/export", dependencies=[Depends(enforce_rate_limit)])
def export_memories(
    fmt: str = Query(default="jsonl", pattern="^(jsonl|csv)$"),
    limit: int = Query(default=5000, ge=1, le=20000),
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("read")),
):
    result = list_memories(db, limit=limit, offset=0)
    if fmt == "csv":
        data = memories_to_csv(result.items)
        return Response(content=data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=memories.csv"})

    data = memories_to_jsonl(result.items)
    return Response(content=data, media_type="application/x-ndjson", headers={"Content-Disposition": "attachment; filename=memories.jsonl"})


@router.get("/context/pull", response_model=ContextPullResponse, dependencies=[Depends(enforce_rate_limit)])
def context_pull_endpoint(
    profile: str = "default",
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("read")),
):
    selected, items = pull_context(db, profile)
    return ContextPullResponse(generated_at=dt.datetime.now(dt.timezone.utc), profile=selected, items=items)


@router.post("/pull-profiles", response_model=PullProfileRead, dependencies=[Depends(enforce_rate_limit)])
def upsert_pull_profile(
    payload: PullProfileCreate,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("admin")),
):
    profile = create_or_update_pull_profile(db, payload)
    return PullProfileRead(
        name=profile.name,
        description=profile.description,
        required_tags=[t for t in profile.required_tags_csv.split(",") if t],
        preferred_sources=[s for s in profile.preferred_sources_csv.split(",") if s],
        max_items=profile.max_items,
        include_pinned=profile.include_pinned,
        lookback_days=profile.lookback_days,
    )


@router.get("/pull-profiles/default", response_model=PullProfileRead, dependencies=[Depends(enforce_rate_limit)])
def default_pull_profile(
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("read")),
):
    return ensure_default_pull_profile(db)


@router.post("/keys", response_model=APIKeyCreateResponse, dependencies=[Depends(enforce_rate_limit)])
def create_key(
    payload: APIKeyCreate,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("admin")),
):
    return create_api_key_record(db, payload)


@router.get("/keys", response_model=list[APIKeyRead], dependencies=[Depends(enforce_rate_limit)])
def list_keys(
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("admin")),
):
    return list_api_keys(db)


@router.delete("/keys/{key_id}", status_code=204, dependencies=[Depends(enforce_rate_limit)])
def revoke_key(
    key_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("admin")),
):
    revoke_api_key(db, key_id)
    return Response(status_code=204)


@router.post("/files/upload", response_model=FileAssetRead, dependencies=[Depends(enforce_rate_limit)])
async def upload_file_endpoint(
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("files")),
):
    if file.content_type not in settings.allowed_mime_set:
        raise HTTPException(status_code=400, detail=f"Unsupported mime type: {file.content_type}")

    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    sha = hashlib.sha256(raw).hexdigest()
    existing = db.scalar(select(FileAsset).where(FileAsset.sha256 == sha))
    if existing:
        return FileAssetRead(
            id=existing.id,
            original_name=existing.original_name,
            mime_type=existing.mime_type,
            size_bytes=existing.size_bytes,
            sha256=existing.sha256,
            description=existing.description,
            uploaded_at=existing.uploaded_at,
        )

    ext = Path(file.filename or "").suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    destination = Path(settings.files_dir) / stored_name
    destination.write_bytes(raw)

    asset = FileAsset(
        original_name=_safe_filename(file.filename or "upload"),
        stored_name=stored_name,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(raw),
        sha256=sha,
        description=description,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return FileAssetRead(
        id=asset.id,
        original_name=asset.original_name,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
        description=asset.description,
        uploaded_at=asset.uploaded_at,
    )


@router.get("/files", response_model=list[FileAssetRead], dependencies=[Depends(enforce_rate_limit)])
def list_files(
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("files")),
):
    files = db.scalars(select(FileAsset).order_by(FileAsset.uploaded_at.desc())).all()
    return [
        FileAssetRead(
            id=f.id,
            original_name=f.original_name,
            mime_type=f.mime_type,
            size_bytes=f.size_bytes,
            sha256=f.sha256,
            description=f.description,
            uploaded_at=f.uploaded_at,
        )
        for f in files
    ]


@router.post("/files/{file_id}/share-links", response_model=FileShareRead, dependencies=[Depends(enforce_rate_limit)])
def create_share_link(
    request: Request,
    file_id: str,
    payload: FileShareCreate,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("files")),
):
    file_asset = db.get(FileAsset, file_id)
    if not file_asset:
        raise HTTPException(status_code=404, detail="File not found")

    token, token_hash = generate_share_token()
    expires_at = None
    if payload.expires_in_hours:
        max_hours = min(payload.expires_in_hours, settings.max_share_expiry_hours)
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=max_hours)
    else:
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=settings.default_share_expiry_hours)

    share = FileShareLink(
        file_id=file_asset.id,
        token_hash=token_hash,
        note=payload.note,
        expires_at=expires_at,
        max_downloads=payload.max_downloads,
        password_hash=hash_password(payload.password) if payload.password else None,
        is_active=True,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    base = settings.base_external_url.rstrip("/") if settings.base_external_url else str(request.base_url).rstrip("/")
    url = f"{base}/share/{token}"

    return FileShareRead(
        id=share.id,
        url=url,
        expires_at=share.expires_at,
        max_downloads=share.max_downloads,
        download_count=share.download_count,
        is_active=share.is_active,
        created_at=share.created_at,
    )


@router.get("/files/{file_id}/share-links", response_model=list[FileShareRead], dependencies=[Depends(enforce_rate_limit)])
def list_share_links(
    request: Request,
    file_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("files")),
):
    file_asset = db.get(FileAsset, file_id)
    if not file_asset:
        raise HTTPException(status_code=404, detail="File not found")

    base = settings.base_external_url.rstrip("/") if settings.base_external_url else str(request.base_url).rstrip("/")
    shares = db.scalars(
        select(FileShareLink).where(FileShareLink.file_id == file_id).order_by(FileShareLink.created_at.desc())
    ).all()

    result: list[FileShareRead] = []
    for share in shares:
        # Returning a non-working placeholder token for historical links is safer than storing plaintext.
        url = f"{base}/share/<hidden-token-{share.id}>"
        result.append(
            FileShareRead(
                id=share.id,
                url=url,
                expires_at=share.expires_at,
                max_downloads=share.max_downloads,
                download_count=share.download_count,
                is_active=share.is_active,
                created_at=share.created_at,
            )
        )
    return result


@router.post("/files/{file_id}/share-links/{share_id}/disable", status_code=204, dependencies=[Depends(enforce_rate_limit)])
def disable_share_link(
    file_id: str,
    share_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_api_scopes("files")),
):
    share = db.get(FileShareLink, share_id)
    if not share or share.file_id != file_id:
        raise HTTPException(status_code=404, detail="Share link not found")

    share.is_active = False
    db.add(share)
    db.commit()
    return Response(status_code=204)
