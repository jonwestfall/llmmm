from __future__ import annotations

import logging
import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import User
from app.routers.api import router as api_router
from app.routers.web import router as web_router
from app.security import hash_password
from app.services import ensure_default_pull_profile

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    cors_origins = settings.cors_origin_list
    allow_credentials = bool(cors_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        https_only=settings.session_cookie_secure,
        same_site="lax",
        max_age=60 * 60 * 12,
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(api_router)
    app.include_router(web_router)

    @app.on_event("startup")
    def startup_event() -> None:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.username == settings.admin_username))
            if not user:
                generated = False
                password = settings.admin_password
                if not password:
                    password = secrets.token_urlsafe(20)
                    generated = True

                user = User(username=settings.admin_username, password_hash=hash_password(password), is_active=True)
                db.add(user)
                db.commit()

                if generated:
                    logger.warning(
                        "Created default admin user '%s' with generated password: %s (change this immediately)",
                        settings.admin_username,
                        password,
                    )
                else:
                    logger.info("Created default admin user '%s' from environment", settings.admin_username)
            elif settings.admin_password and settings.admin_password_force_reset:
                user.password_hash = hash_password(settings.admin_password)
                user.is_active = True
                db.add(user)
                db.commit()
                logger.warning(
                    "Reset password for existing admin user '%s' due to LLMMM_ADMIN_PASSWORD_FORCE_RESET=true",
                    settings.admin_username,
                )

            ensure_default_pull_profile(db)
            db.commit()

    return app


app = create_app()
