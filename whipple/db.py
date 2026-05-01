"""SQLAlchemy session + init_db()."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base

DB_PATH = os.getenv("WHIPPLE_DB", "/app/data/whipple.db")
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=ENGINE, autocommit=False, autoflush=False))


def init_db():
    """Create all tables. Idempotent."""
    Base.metadata.create_all(ENGINE)


def get_session():
    return SessionLocal()
