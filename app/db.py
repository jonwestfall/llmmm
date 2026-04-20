from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
