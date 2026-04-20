from __future__ import annotations

import os

os.environ.setdefault("LLMMM_DATABASE_URL", "sqlite:///./data/test_llmmm.db")
os.environ.setdefault("LLMMM_ADMIN_PASSWORD", "admin-test-password")
os.environ.setdefault("LLMMM_SESSION_SECRET", "test-session-secret")
os.environ.setdefault("LLMMM_SECRET_KEY", "test-secret-key")
os.environ.setdefault("LLMMM_DEBUG", "true")
os.environ.setdefault("LLMMM_BASE_EXTERNAL_URL", "http://testserver")

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import create_app
from app.schemas import APIKeyCreate
from app.services import create_api_key_record


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _bootstrap_key() -> str:
    with SessionLocal() as db:
        created = create_api_key_record(
            db,
            APIKeyCreate(name="pytest", scopes=["read", "write", "files", "admin"], source_hint="tests"),
        )
        return created.key


def test_memory_create_list_and_pull() -> None:
    _reset_db()

    app = create_app()
    with TestClient(app) as client:
        key = _bootstrap_key()
        headers = {"X-API-Key": key}

        create = client.post(
            "/api/v1/memories",
            headers=headers,
            json={
                "title": "Writing Style",
                "body": "Prefer concise, direct prose.",
                "source_model": "chatgpt",
                "tags": ["style", "writing"],
                "importance": 5,
                "pinned": True,
                "metadata": {"owner": "jon"},
            },
        )
        assert create.status_code == 200
        memory = create.json()
        assert memory["title"] == "Writing Style"

        listing = client.get("/api/v1/memories", headers=headers)
        assert listing.status_code == 200
        data = listing.json()
        assert data["total"] >= 1

        pulled = client.get("/api/v1/context/pull?profile=default", headers=headers)
        assert pulled.status_code == 200
        pull_data = pulled.json()
        assert pull_data["profile"]["name"] == "default"
        assert len(pull_data["items"]) >= 1


def test_file_upload_and_share_link() -> None:
    _reset_db()

    app = create_app()
    with TestClient(app) as client:
        key = _bootstrap_key()
        headers = {"X-API-Key": key}

        upload = client.post(
            "/api/v1/files/upload",
            headers=headers,
            files={"file": ("style-guide.txt", b"hello world", "text/plain")},
            data={"description": "test file"},
        )
        assert upload.status_code == 200
        file_obj = upload.json()

        share = client.post(
            f"/api/v1/files/{file_obj['id']}/share-links",
            headers=headers,
            json={"expires_in_hours": 1, "max_downloads": 2},
        )
        assert share.status_code == 200
        share_url = share.json()["url"]
        token = share_url.rsplit("/", 1)[-1]

        fetched = client.get(f"/share/{token}")
        assert fetched.status_code == 200
        assert fetched.content == b"hello world"
