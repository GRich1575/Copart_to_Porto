"""Engine and session factory. PostgreSQL in production; any SQLAlchemy URL works for tests."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from vehicle_intelligence.models import Base


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_schema(engine: Engine) -> list[str]:
    """Create all missing tables. Returns sorted table names present afterwards."""
    Base.metadata.create_all(engine)
    return sorted(inspect(engine).get_table_names())
