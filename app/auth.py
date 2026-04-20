from __future__ import annotations

import datetime as dt
import threading
from collections import deque
from typing import Callable

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import APIKey, User
from app.security import hash_token, normalize_scopes, verify_password


class SimpleRateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.requests_per_minute:
                return False
            bucket.append(now)
            return True


rate_limiter = SimpleRateLimiter(settings.rate_limit_requests_per_minute)


def enforce_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def get_api_key_record(request: Request, db: Session = Depends(get_db)) -> APIKey:
    header_key = request.headers.get("x-api-key")
    auth_header = request.headers.get("authorization", "")

    token: str | None = None
    if header_key:
        token = header_key.strip()
    elif auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    key_hash = hash_token(token)
    api_key = db.scalar(select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active.is_(True)))
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    api_key.last_used_at = dt.datetime.now(dt.timezone.utc)
    db.add(api_key)
    db.commit()
    return api_key


def require_api_scopes(*required_scopes: str) -> Callable[[APIKey], APIKey]:
    normalized_required = set(normalize_scopes(required_scopes))

    def _dependency(api_key: APIKey = Depends(get_api_key_record)) -> APIKey:
        available = set(normalize_scopes(api_key.scopes_csv.split(",")))
        if not normalized_required.issubset(available):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient API key scope")
        return api_key

    return _dependency


class WebAuthRequired:
    def __call__(self, user: User = Depends(get_current_user)) -> User:
        return user


web_auth_required = WebAuthRequired()
