"""Integration tests for TRACE v0.3 FastAPI Session endpoints."""

import io
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from trace.api.app import create_app
from trace.db.models import Base
from trace.db.session import configure_db, get_db_session


@pytest_asyncio.fixture
async def test_client(tmp_path: Path):
    """Create test client with isolated SQLite database."""
    test_db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_api.db'}"
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
async def test_api_health_check(test_client: AsyncClient):
    """Test health endpoint."""
    response = await test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.3.0"


@pytest.mark.asyncio
async def test_create_and_get_session(test_client: AsyncClient):
    """Test creating session via JSON and fetching detail."""
    payload = {
        "user_goal": "Investigate AttributeError in user profile",
        "source_code": "def get_name(u): return u.get('name').upper()",
        "title": "Profile None Bug",
        "error_description": "AttributeError on NoneType",
    }
    create_res = await test_client.post("/api/sessions", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    session_id = created_data["id"]
    assert session_id.startswith("trace_sess_")
    assert created_data["status"] == "CREATED"
    assert created_data["title"] == "Profile None Bug"

    # Fetch detail
    get_res = await test_client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["id"] == session_id
    assert detail["user_goal"] == payload["user_goal"]


@pytest.mark.asyncio
async def test_create_session_from_upload(test_client: AsyncClient):
    """Test creating session via file upload."""
    file_content = b"def sum_all(nums):\n    return sum(nums)\n"
    files = {
        "file": ("test_script.py", io.BytesIO(file_content), "text/x-python"),
    }
    data = {
        "user_goal": "Test script upload",
    }
    response = await test_client.post("/api/sessions/upload", files=files, data=data)
    assert response.status_code == 201
    res_data = response.json()
    assert "test_script" in res_data["title"]
    assert res_data["source_code"] == file_content.decode("utf-8")


@pytest.mark.asyncio
async def test_upload_rejects_non_py_and_oversize(test_client: AsyncClient):
    """Test upload validation rejects non-.py files and oversized uploads."""
    # Non-py rejection
    files = {"file": ("malicious.exe", io.BytesIO(b"binary"), "application/octet-stream")}
    res = await test_client.post("/api/sessions/upload", files=files, data={"user_goal": "Test"})
    assert res.status_code == 400

    # Oversize rejection (>256KB)
    huge_bytes = b"a" * (300 * 1024)
    huge_files = {"file": ("huge.py", io.BytesIO(huge_bytes), "text/x-python")}
    res_huge = await test_client.post("/api/sessions/upload", files=huge_files, data={"user_goal": "Test"})
    assert res_huge.status_code == 400


@pytest.mark.asyncio
async def test_list_and_delete_sessions(test_client: AsyncClient):
    """Test listing historical sessions and deleting a session."""
    # Create 2 sessions
    await test_client.post("/api/sessions", json={"user_goal": "Goal 1", "source_code": "a=1"})
    res2 = await test_client.post("/api/sessions", json={"user_goal": "Goal 2", "source_code": "b=2"})
    sess_id_2 = res2.json()["id"]

    list_res = await test_client.get("/api/sessions")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data["sessions"]) >= 2

    # Delete 1 session
    del_res = await test_client.delete(f"/api/sessions/{sess_id_2}")
    assert del_res.status_code == 204

    # Verify 404 on deleted
    del_check = await test_client.get(f"/api/sessions/{sess_id_2}")
    assert del_check.status_code == 404


@pytest.mark.asyncio
async def test_start_investigation_and_background_completion(test_client: AsyncClient):
    """Test starting an investigation and asserting completion and diagnosis persistence."""
    create_res = await test_client.post("/api/sessions", json={
        "user_goal": "Investigate syntax error",
        "source_code": "def calculate(total)\n    return total",
    })
    session_id = create_res.json()["id"]

    # Start investigation with mock provider
    inv_res = await test_client.post(f"/api/sessions/{session_id}/investigate", json={"provider": "mock"})
    assert inv_res.status_code == 200
    assert inv_res.json()["status"] == "RUNNING"

    # Prevent duplicate start while running
    dup_res = await test_client.post(f"/api/sessions/{session_id}/investigate", json={"provider": "mock"})
    assert dup_res.status_code == 409

    # Allow background task to complete
    import asyncio
    for _ in range(20):
        await asyncio.sleep(0.1)
        check = await test_client.get(f"/api/sessions/{session_id}")
        if check.json()["status"] in ("COMPLETED", "FAILED"):
            break

    final_detail = (await test_client.get(f"/api/sessions/{session_id}")).json()
    assert final_detail["status"] == "COMPLETED"
    assert final_detail["confidence"] >= 0.8
    assert final_detail["diagnosis"] is not None
    assert "syntax" in final_detail["diagnosis"]["likely_root_cause"].lower()
    assert len(final_detail["plan_steps"]) >= 1
