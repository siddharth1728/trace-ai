"""Integration tests for full v0.5 Interactive Debugging Session workflow."""

import pytest
from trace.api.schemas import (
    CreateCodeRevisionRequest,
    CreateSessionRequest,
    CreateStudentHypothesisRequest,
    CreateStudentTestInputRequest,
)
from trace.services.session_service import SessionService


@pytest.mark.asyncio
async def test_full_interactive_debugging_workflow(async_db_session):
    """Test full multi-turn student interactive debugging session."""
    service = SessionService(async_db_session)

    buggy_code = (
        "def get_user_profile(user_db, user_id):\n"
        "    user = user_db.get(user_id)\n"
        "    return {'name': user.get('name').upper()}\n"
    )

    # 1. Create session in INTERACTIVE mode
    create_req = CreateSessionRequest(
        user_goal="Debug crash when formatting user name",
        source_code=buggy_code,
        title="Interactive Test Session",
        mode="INTERACTIVE",
    )
    detail = await service.create_session(create_req)
    session_id = detail.id
    assert detail.mode == "INTERACTIVE"
    assert len(detail.revisions) == 1
    assert detail.revisions[0].revision_number == 1
    assert len(detail.interaction_turns) == 1
    assert detail.interaction_turns[0].action_type == "SUBMIT_INITIAL_BUG"

    # 2. Student Formulates Hypothesis
    hyp_req = CreateStudentHypothesisRequest(
        hypothesis_text="user.get('name') returns None for missing name, causing AttributeError on .upper()",
        target_function_or_line="get_user_profile",
        student_confidence=0.85,
    )
    shyp_dto = await service.submit_student_hypothesis(session_id, hyp_req)
    assert shyp_dto.turn_number == 2
    assert "user.get('name')" in shyp_dto.hypothesis_text

    # 3. Student Runs a Custom Sandbox Test Case
    test_req = CreateStudentTestInputRequest(
        input_expression="get_user_profile({1: {}}, 1)",
        student_rationale="Calling with empty dictionary to verify None behavior",
        is_boundary_case=True,
    )
    test_res = await service.submit_student_test_input(session_id, test_req)
    assert test_res.executed is True
    # Should trigger AttributeError in the buggy code
    assert test_res.execution_success is False
    assert test_res.exception_type == "AttributeError"

    # 4. Student Submits a Corrected Code Revision
    fixed_code = (
        "def get_user_profile(user_db, user_id):\n"
        "    user = user_db.get(user_id, {})\n"
        "    name = user.get('name')\n"
        "    return {'name': name.upper() if name else 'ANONYMOUS'}\n"
    )
    rev_req = CreateCodeRevisionRequest(
        source_code=fixed_code,
        intent_notes="Added fallback for missing user or missing name",
        time_since_previous_sec=45.0,
    )
    rev_dto = await service.submit_code_revision(session_id, rev_req)
    assert rev_dto.revision_number == 2
    assert rev_dto.lines_added > 0
    assert rev_dto.execution_success is True

    # 5. Verify Full Snapshot & Deterministic Activity Metrics
    full_session = await service.get_session(session_id)
    assert full_session is not None
    assert full_session.mode == "INTERACTIVE"
    assert len(full_session.student_hypotheses) == 1
    assert len(full_session.revisions) == 2
    assert len(full_session.student_test_inputs) == 1
    assert len(full_session.interaction_turns) == 4

    assert full_session.student_activity is not None
    assert full_session.student_activity.revisions_count == 2
    assert full_session.student_activity.hypotheses_count == 1
    assert full_session.student_activity.custom_tests_count == 1
    assert full_session.student_activity.boundary_tests_count == 1
    assert full_session.student_activity.total_turns == 4
