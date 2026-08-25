"""Integration tests for /api/profile and telemetry endpoints."""

from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from trace.api.app import create_app
from trace.db.models import Base
from trace.db.session import configure_db, get_db_session


@pytest_asyncio.fixture
async def test_client(tmp_path: Path):
    """Create test client with isolated SQLite database."""
    test_db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_profile_api.db'}"
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
async def test_get_student_profile_empty(test_client: AsyncClient):
    resp = await test_client.get("/api/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert "deterministic_habits" in data
    assert "key_strengths" in data
    assert "growth_areas" in data


@pytest.mark.asyncio
async def test_session_lifecycle_creates_telemetry_and_updates_profile(test_client: AsyncClient):
    # 1. Create a session
    create_resp = await test_client.post(
        "/api/sessions",
        json={
            "source_code": "def divide(a, b):\n    return a / b\nprint(divide(1, 0))",
            "user_goal": "Debug ZeroDivisionError in divide",
            "error_description": "ZeroDivisionError: division by zero",
            "traceback_input": "Traceback:\n  File 'test.py', line 2, in divide\nZeroDivisionError",
        },
    )
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    # 2. Run investigation to completion
    start_resp = await test_client.post(f"/api/sessions/{session_id}/investigate", json={"provider": "mock"})
    assert start_resp.status_code == 200

    import asyncio
    for _ in range(25):
        await asyncio.sleep(0.1)
        check = await test_client.get(f"/api/sessions/{session_id}")
        if check.json()["status"] in ("COMPLETED", "FAILED"):
            break

    # 3. Retrieve telemetry for the session
    telem_resp = await test_client.get(f"/api/sessions/{session_id}/telemetry")
    assert telem_resp.status_code == 200
    telem_data = telem_resp.json()
    assert telem_data["session_id"] == session_id
    assert telem_data["has_traceback_input"] is True
    assert telem_data["loc"] >= 3

    # 4. Check profile reflects the new session
    prof_resp = await test_client.get("/api/profile")
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()
    assert prof_data["deterministic_habits"]["total_sessions"] >= 1
