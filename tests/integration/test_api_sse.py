"""Integration tests for TRACE v0.3 Server-Sent Events (SSE) stream endpoint."""

import asyncio
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from trace.api.app import create_app
from trace.db.models import Base
from trace.db.session import configure_db, get_db_session


@pytest_asyncio.fixture
async def sse_test_client(tmp_path: Path):
    """Create test client with isolated database for SSE streaming tests."""
    test_db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_sse.db'}"
    session_maker = configure_db(test_db_url)
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await engine.dispose()


@pytest.mark.asyncio
async def test_sse_streaming_completed_session(sse_test_client: AsyncClient):
    """Test connecting to SSE endpoint for a session that has already finished."""
    create_res = await sse_test_client.post("/api/sessions", json={
        "user_goal": "Investigate runtime bug",
        "source_code": "print(10/0)",
    })
    session_id = create_res.json()["id"]

    # Start investigation and wait for completion
    await sse_test_client.post(f"/api/sessions/{session_id}/investigate", json={"provider": "mock"})

    for _ in range(20):
        await asyncio.sleep(0.1)
        res = await sse_test_client.get(f"/api/sessions/{session_id}")
        if res.json()["status"] == "COMPLETED":
            break

    # Connect to SSE endpoint
    sse_response = await sse_test_client.get(f"/api/sessions/{session_id}/events")
    assert sse_response.status_code == 200
    assert "text/event-stream" in sse_response.headers.get("content-type", "")
    content = sse_response.text

    assert "event: session_status" in content
    assert "event: diagnosis_ready" in content
    assert "event: session_completed" in content
