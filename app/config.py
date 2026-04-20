from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LLMMM"
    environment: str = "production"
    debug: bool = False

    secret_key: str = "change-me-in-production"
    session_secret: str = "change-me-too"
    session_https_only: Optional[bool] = None

    database_url: str = "sqlite:///./data/llmmm.db"

    data_dir: str = "./data"
    files_dir: str = "./data/files"
    backup_dir: str = "./data/backups"

    max_upload_mb: int = 25
    allowed_upload_mimes: str = (
        "application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    default_share_expiry_hours: int = 168
    max_share_expiry_hours: int = 24 * 365

    rate_limit_requests_per_minute: int = 120

    cors_origins: str = ""

    admin_username: str = "admin"
    admin_password: str = ""

    api_key_prefix: str = "llmmm"

    base_external_url: str = ""

    model_config = SettingsConfigDict(env_prefix="LLMMM_", case_sensitive=False)

    @field_validator("environment")
    @classmethod
    def validate_env(cls, v: str) -> str:
        return v.lower().strip()

    @property
    def allowed_mime_set(self) -> set[str]:
        return {m.strip() for m in self.allowed_upload_mimes.split(",") if m.strip()}

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def session_cookie_secure(self) -> bool:
        if self.session_https_only is not None:
            return self.session_https_only
        return self.base_external_url.strip().lower().startswith("https://")

    def ensure_dirs(self) -> None:
        for p in [self.data_dir, self.files_dir, self.backup_dir]:
            Path(p).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings


settings = get_settings()
