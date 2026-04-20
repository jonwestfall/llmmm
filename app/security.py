from __future__ import annotations

import hashlib
import secrets
from typing import Iterable

from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


ALLOWED_SCOPES = {"read", "write", "files", "admin"}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def generate_api_key() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    full = f"{settings.api_key_prefix}_{raw}"
    return full, hash_token(full)


def generate_share_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_scopes(scopes: Iterable[str]) -> list[str]:
    clean = []
    for scope in scopes:
        value = scope.strip().lower()
        if value and value in ALLOWED_SCOPES and value not in clean:
            clean.append(value)
    return clean or ["read"]
