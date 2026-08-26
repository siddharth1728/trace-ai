"""Unit tests for CodeRevision domain models and persistence in TRACE v0.5."""

import pytest
from trace.core.models import CodeRevision
from trace.db.repository import SessionRepository


def test_code_revision_model_defaults():
    rev = CodeRevision(
        revision_number=1,
        source_code="def solve(): pass",
        intent_notes="Initial submission",
        lines_added=1,
        total_loc=1,
    )
    assert rev.revision_number == 1
    assert rev.execution_success is False
    assert rev.resolved_error is False


@pytest.mark.asyncio
async def test_code_revisions_sequential_tracking(async_db_session):
    repo = SessionRepository(async_db_session)
    sess = await repo.create_session(
        session_id="sess_rev_test",
        user_goal="Test code revision chain",
        source_code="def f(): return 1\n",
        mode="INTERACTIVE",
    )

    # Revision 1
    rev1 = await repo.add_code_revision(
        session_id="sess_rev_test",
        source_code="def f(): return 1\n",
        intent_notes="Initial bug",
        revision_number=1,
        lines_added=1,
        total_loc=1,
    )
    assert rev1.revision_number == 1

    # Revision 2 (Auto revision numbering)
    rev2 = await repo.add_code_revision(
        session_id="sess_rev_test",
        source_code="def f():\n    # Fix\n    return 2\n",
        intent_notes="Fixed return value",
        lines_added=2,
        lines_modified=1,
        total_loc=2,
        execution_success=True,
    )
    assert rev2.revision_number == 2

    # Verify listing
    revs = await repo.list_code_revisions("sess_rev_test")
    assert len(revs) == 2
    assert revs[0].revision_number == 1
    assert revs[1].revision_number == 2

    # Latest revision
    latest = await repo.get_latest_code_revision("sess_rev_test")
    assert latest.id == rev2.id
    assert "Fixed return value" in latest.intent_notes
