"""Pytest configuration and fixtures for TRACE test suite."""

import os
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from trace.db.models import Base
from trace.tools.registry import create_default_registry


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Fixture providing a clean temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def default_registry(temp_workspace: Path):
    """Fixture providing a default tool registry configured for temp workspace."""
    return create_default_registry(workspace_root=str(temp_workspace))


@pytest_asyncio.fixture
async def async_db_session(tmp_path: Path):
    """Fixture providing an isolated in-memory or temp SQLite async database session."""
    db_file = tmp_path / "test_trace.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    engine = create_async_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
