"""Database engine and sessionmaker management for TRACE v0.3."""

from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from trace.db.models import Base

# Default database file path
DEFAULT_DB_FILE = Path.cwd() / "trace.db"
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_FILE}"

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(db_url: str = DEFAULT_DB_URL) -> AsyncEngine:
    """Get or create singleton async database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
    return _engine


def configure_db(db_url: str) -> async_sessionmaker[AsyncSession]:
    """Configure or re-bind singleton engine and sessionmaker to a specific db URL."""
    global _engine, _session_factory
    _engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _session_factory


def get_session_factory(db_url: str = DEFAULT_DB_URL) -> async_sessionmaker[AsyncSession]:
    """Get or create singleton async sessionmaker."""
    global _session_factory
    if _session_factory is None:
        configure_db(db_url)
    return _session_factory


async def init_db(db_url: str = DEFAULT_DB_URL) -> None:
    """Initialize database tables."""
    engine = get_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session(db_url: str = DEFAULT_DB_URL) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding async database sessions."""
    factory = get_session_factory(db_url)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
