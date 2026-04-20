from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import authenticate_user, web_auth_required
from app.config import settings
from app.db import get_db
from app.models import FileAsset, FileShareLink, Memory
from app.schemas import APIKeyCreate, FileShareCreate, MemoryCreate, MemoryUpdate
from app.security import generate_share_token, hash_password
from app.services import (
    create_api_key_record,
    create_memory,
    list_api_keys,
    list_memories,
    revoke_api_key,
    serialize_memory,
    update_memory,
)


router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


def _csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(24)
        request.session["csrf_token"] = token
    return token


def _validate_csrf(request: Request, token: str) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not secrets.compare_digest(expected, token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")


def _redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def _safe_filename(name: str) -> str:
    keep = [c for c in name if c.isalnum() or c in {"-", "_", "."}]
    cleaned = "".join(keep).strip(".")
    return cleaned or "file"


def _utcnow_for(dt_value: dt.datetime) -> dt.datetime:
    if dt_value.tzinfo is None:
        return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    return dt.datetime.now(dt.timezone.utc)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return _redirect("/")
    return templates.TemplateResponse("login.html", {"request": request, "csrf_token": _csrf_token(request), "error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    _validate_csrf(request, csrf_token)
    user = authenticate_user(db, username=username.strip(), password=password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": _csrf_token(request),
                "error": "Invalid username or password",
            },
            status_code=401,
        )

    request.session["user_id"] = user.id
    return _redirect("/")


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    _validate_csrf(request, csrf_token)
    request.session.clear()
    return _redirect("/login")


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: str | None = None,
    source_model: str | None = None,
    pinned: bool | None = None,
    tag: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    tags = [tag] if tag else []
    result = list_memories(db, q=q, tags=tags, source_model=source_model, pinned=pinned, limit=200)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "csrf_token": _csrf_token(request),
            "memories": result.items,
            "total": result.total,
            "query": q or "",
            "source_model": source_model or "",
            "tag": tag or "",
            "pinned": pinned,
            "flash": request.session.pop("flash", None),
        },
    )


@router.post("/memories")
def create_memory_web(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    source_model: str | None = Form(default=None),
    tags: str = Form(default=""),
    importance: int = Form(default=3),
    pinned: bool = Form(default=False),
    metadata_json: str = Form(default="{}"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    _validate_csrf(request, csrf_token)
    try:
        metadata = {} if not metadata_json.strip() else json.loads(metadata_json)
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a JSON object")
    except Exception as exc:  # pragma: no cover - defensive
        request.session["flash"] = f"Could not parse metadata JSON: {exc}"
        return _redirect("/")

    payload = MemoryCreate(
        title=title,
        body=body,
        source_model=source_model or None,
        tags=[t.strip().lower() for t in tags.split(",") if t.strip()],
        importance=max(1, min(5, importance)),
        pinned=bool(pinned),
        metadata=metadata,
    )

    create_memory(db, payload)
    request.session["flash"] = "Memory saved"
    return _redirect("/")


@router.get("/memories/{memory_id}", response_class=HTMLResponse)
def edit_memory_page(
    request: Request,
    memory_id: str,
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    memory = db.get(Memory, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return templates.TemplateResponse(
        "memory_edit.html",
        {
            "request": request,
            "csrf_token": _csrf_token(request),
            "memory": serialize_memory(memory),
            "metadata_json": json.dumps(memory.metadata_json or {}, indent=2),
            "flash": request.session.pop("flash", None),
        },
    )


@router.post("/memories/{memory_id}")
def update_memory_web(
    request: Request,
    memory_id: str,
    title: str = Form(...),
    body: str = Form(...),
    source_model: str | None = Form(default=None),
    tags: str = Form(default=""),
    importance: int = Form(default=3),
    pinned: bool = Form(default=False),
    metadata_json: str = Form(default="{}"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    _validate_csrf(request, csrf_token)

    memory = db.get(Memory, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    try:
        metadata = {} if not metadata_json.strip() else json.loads(metadata_json)
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a JSON object")
    except Exception as exc:
        request.session["flash"] = f"Could not parse metadata JSON: {exc}"
        return _redirect(f"/memories/{memory_id}")

    payload = MemoryUpdate(
        title=title,
        body=body,
        source_model=source_model or None,
        tags=[t.strip().lower() for t in tags.split(",") if t.strip()],
        importance=max(1, min(5, importance)),
        pinned=bool(pinned),
        metadata=metadata,
    )
    update_memory(db, memory, payload)
    request.session["flash"] = "Memory updated"
    return _redirect(f"/memories/{memory_id}")


@router.post("/memories/{memory_id}/delete")
def delete_memory_web(
    request: Request,
    memory_id: str,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    _validate_csrf(request, csrf_token)
    memory = db.get(Memory, memory_id)
    if memory:
        db.delete(memory)
        db.commit()
    request.session["flash"] = "Memory deleted"
    return _redirect("/")


@router.get("/keys", response_class=HTMLResponse)
def keys_page(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    return templates.TemplateResponse(
        "keys.html",
        {
            "request": request,
            "csrf_token": _csrf_token(request),
            "keys": list_api_keys(db),
            "new_key": request.session.pop("new_key", None),
            "flash": request.session.pop("flash", None),
        },
    )


@router.post("/keys")
def create_key_web(
    request: Request,
    name: str = Form(...),
    scopes: str = Form(default="read,write,files"),
    source_hint: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    _validate_csrf(request, csrf_token)
    payload = APIKeyCreate(name=name, scopes=[s.strip() for s in scopes.split(",")], source_hint=source_hint)
    result = create_api_key_record(db, payload)
    request.session["new_key"] = result.key
    request.session["flash"] = "API key created. Copy it now; it will not be shown again."
    return _redirect("/keys")


@router.post("/keys/{key_id}/revoke")
def revoke_key_web(
    request: Request,
    key_id: str,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    _validate_csrf(request, csrf_token)
    revoke_api_key(db, key_id)
    request.session["flash"] = "Key revoked"
    return _redirect("/keys")


@router.get("/files", response_class=HTMLResponse)
def files_page(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    files = db.scalars(select(FileAsset).order_by(FileAsset.uploaded_at.desc())).all()
    return templates.TemplateResponse(
        "files.html",
        {
            "request": request,
            "csrf_token": _csrf_token(request),
            "files": files,
            "flash": request.session.pop("flash", None),
            "share_link": request.session.pop("share_link", None),
        },
    )


@router.post("/files/upload")
async def upload_file_web(
    request: Request,
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    _validate_csrf(request, csrf_token)

    if file.content_type not in settings.allowed_mime_set:
        request.session["flash"] = f"Unsupported mime type: {file.content_type}"
        return _redirect("/files")

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        request.session["flash"] = f"File too large. Max is {settings.max_upload_mb} MB"
        return _redirect("/files")

    sha = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(FileAsset).where(FileAsset.sha256 == sha))
    if existing:
        request.session["flash"] = "File already exists"
        return _redirect("/files")

    ext = Path(file.filename or "").suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    destination = Path(settings.files_dir) / stored_name
    destination.write_bytes(content)

    asset = FileAsset(
        original_name=_safe_filename(file.filename or "upload"),
        stored_name=stored_name,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        sha256=sha,
        description=description,
    )
    db.add(asset)
    db.commit()
    request.session["flash"] = "File uploaded"
    return _redirect("/files")


@router.post("/files/{file_id}/share")
def create_share_web(
    request: Request,
    file_id: str,
    expires_in_hours: int | None = Form(default=None),
    max_downloads: int | None = Form(default=None),
    password: str | None = Form(default=None),
    note: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    _validate_csrf(request, csrf_token)

    file_asset = db.get(FileAsset, file_id)
    if not file_asset:
        request.session["flash"] = "File not found"
        return _redirect("/files")

    token, token_hash = generate_share_token()

    if expires_in_hours:
        expiry_hours = min(max(1, expires_in_hours), settings.max_share_expiry_hours)
    else:
        expiry_hours = settings.default_share_expiry_hours

    share = FileShareLink(
        file_id=file_id,
        token_hash=token_hash,
        note=note,
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=expiry_hours),
        max_downloads=max_downloads,
        password_hash=hash_password(password) if password else None,
        is_active=True,
    )
    db.add(share)
    db.commit()

    base = settings.base_external_url.rstrip("/") if settings.base_external_url else str(request.base_url).rstrip("/")
    request.session["share_link"] = f"{base}/share/{token}"
    request.session["flash"] = "Share link created"
    return _redirect("/files")


@router.post("/files/{file_id}/shares/{share_id}/disable")
def disable_share_web(
    request: Request,
    file_id: str,
    share_id: str,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(web_auth_required),
):
    _validate_csrf(request, csrf_token)

    share = db.get(FileShareLink, share_id)
    if share and share.file_id == file_id:
        share.is_active = False
        db.add(share)
        db.commit()

    request.session["flash"] = "Share link disabled"
    return _redirect("/files")


@router.get("/share/{token}")
def public_share_download(
    request: Request,
    token: str,
    password: str | None = None,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    share = db.scalar(select(FileShareLink).where(FileShareLink.token_hash == token_hash, FileShareLink.is_active.is_(True)))
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")

    if share.expires_at and share.expires_at < _utcnow_for(share.expires_at):
        raise HTTPException(status_code=410, detail="Share link expired")

    if share.max_downloads is not None and share.download_count >= share.max_downloads:
        raise HTTPException(status_code=410, detail="Share link download limit reached")

    if share.password_hash:
        from app.security import verify_password

        if not password or not verify_password(password, share.password_hash):
            raise HTTPException(status_code=401, detail="Password required or incorrect")

    asset = db.get(FileAsset, share.file_id)
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")

    path = Path(settings.files_dir) / asset.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File content missing")

    share.download_count += 1
    db.add(share)
    db.commit()

    return FileResponse(path=path, filename=asset.original_name, media_type=asset.mime_type)
