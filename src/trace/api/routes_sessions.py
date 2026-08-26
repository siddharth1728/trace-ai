"""FastAPI route handlers for TRACE debugging sessions and SSE streaming."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from trace.api.schemas import (
    AnswerSocraticRequest,
    CodeRevisionDTO,
    CreateCodeRevisionRequest,
    CreateSessionRequest,
    CreateStudentHypothesisRequest,
    CreateStudentTestInputRequest,
    ErrorResponse,
    InteractiveTimelineResponse,
    InvestigateRequest,
    InvestigationStartedResponse,
    RevisionsListResponse,
    SessionDetailResponse,
    SessionListResponse,
    StudentHypothesisDTO,
    StudentTestExecutionResponse,
)
from trace.db.session import get_db_session
from trace.services.event_broadcaster import global_broadcaster
from trace.services.session_service import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_session_service(db: AsyncSession = Depends(get_db_session)) -> SessionService:
    """Dependency injecting SessionService with current database session."""
    return SessionService(db)


@router.post(
    "",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new debugging session from text source",
)
async def create_session(
    request: CreateSessionRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """Create a new debugging session with Python source code and user goal."""
    return await service.create_session(request)


@router.post(
    "/upload",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new debugging session from uploaded Python file",
)
async def create_session_from_upload(
    file: UploadFile = File(...),
    user_goal: str = Form(...),
    error_description: Optional[str] = Form(None),
    traceback_input: Optional[str] = Form(None),
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """Upload a .py file and create an investigation session."""
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Python (.py) source files are allowed.",
        )

    content = await file.read()
    try:
        return await service.create_session_from_upload(
            filename=file.filename,
            content_bytes=content,
            user_goal=user_goal,
            error_description=error_description,
            traceback_input=traceback_input,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List historical debugging sessions",
)
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    """Retrieve paginated list of past debugging investigations."""
    return await service.list_sessions(limit=limit, offset=offset)


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get complete session snapshot and investigation status",
    responses={404: {"model": ErrorResponse}},
)
async def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """Retrieve full details, plan, observations, evidence, and diagnosis for a session."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debugging session '{session_id}' not found.",
        )
    return session


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a debugging session",
)
async def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> None:
    """Delete a session and all its associated investigation data."""
    deleted = await service.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debugging session '{session_id}' not found.",
        )


@router.post(
    "/{session_id}/investigate",
    response_model=InvestigationStartedResponse,
    summary="Start an automated evidence-driven investigation",
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def start_investigation(
    session_id: str,
    request: InvestigateRequest = InvestigateRequest(),
    service: SessionService = Depends(get_session_service),
) -> InvestigationStartedResponse:
    """Launch the TRACE agent investigation loop in the background."""
    try:
        await service.start_investigation(
            session_id=session_id,
            provider_name=request.provider,
            max_iterations=request.max_iterations,
        )
        return InvestigationStartedResponse(
            session_id=session_id,
            status="RUNNING",
            message=f"Investigation started for session '{session_id}'.",
        )
    except KeyError as k_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(k_err))
    except RuntimeError as r_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(r_err))


@router.get(
    "/{session_id}/events",
    summary="Server-Sent Events (SSE) live investigation progress stream",
)
async def stream_session_events(
    session_id: str,
    service: SessionService = Depends(get_session_service),
):
    """
    Subscribe to live real-time Server-Sent Events for this investigation session.
    Streams plan creation, tool executions, observation records, hypotheses, and diagnosis.
    """
    # Verify session exists
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debugging session '{session_id}' not found.",
        )

    async def sse_event_generator():
        # If session is already complete, emit initial snapshot
        if session.status in ("COMPLETED", "FAILED", "BLOCKED"):
            yield f"event: session_status\ndata: {json.dumps({'status': session.status, 'session_id': session_id})}\n\n"
            if session.diagnosis:
                yield f"event: diagnosis_ready\ndata: {json.dumps(session.diagnosis.model_dump())}\n\n"
            yield f"event: session_completed\ndata: {json.dumps({'status': session.status, 'confidence': session.confidence})}\n\n"
            return

        # Stream live events from broadcaster
        async for event in global_broadcaster.subscribe(session_id):
            event_type = event.get("event_type", "message")
            event_json = json.dumps(event)
            yield f"event: {event_type}\ndata: {event_json}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Milestone v0.5 Interactive Student Debugging Turn Routes
# ============================================================================

@router.post(
    "/{session_id}/turns/hypothesis",
    response_model=StudentHypothesisDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a student-articulated hypothesis",
)
async def submit_hypothesis(
    session_id: str,
    request: CreateStudentHypothesisRequest,
    service: SessionService = Depends(get_session_service),
) -> StudentHypothesisDTO:
    """Record a hypothesis formulated by the student."""
    try:
        return await service.submit_student_hypothesis(session_id, request)
    except KeyError as k_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(k_err))


@router.post(
    "/{session_id}/turns/revision",
    response_model=CodeRevisionDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a modified code revision",
)
async def submit_code_revision(
    session_id: str,
    request: CreateCodeRevisionRequest,
    service: SessionService = Depends(get_session_service),
) -> CodeRevisionDTO:
    """Process, diff, and test-execute a student code modification."""
    try:
        return await service.submit_code_revision(session_id, request)
    except KeyError as k_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(k_err))


@router.post(
    "/{session_id}/turns/test-input",
    response_model=StudentTestExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Propose and execute a custom student test input",
)
async def submit_test_input(
    session_id: str,
    request: CreateStudentTestInputRequest,
    service: SessionService = Depends(get_session_service),
) -> StudentTestExecutionResponse:
    """Run a student-proposed test case in the isolated execution sandbox."""
    try:
        return await service.submit_student_test_input(session_id, request)
    except KeyError as k_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(k_err))


@router.post(
    "/{session_id}/turns/answer-socratic",
    response_model=SessionDetailResponse,
    summary="Answer or skip a Socratic question",
)
async def answer_socratic_prompt(
    session_id: str,
    request: AnswerSocraticRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """Record response to a reflective inquiry from TRACE."""
    try:
        return await service.answer_socratic_prompt(session_id, request)
    except KeyError as k_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(k_err))


@router.get(
    "/{session_id}/revisions",
    response_model=RevisionsListResponse,
    summary="List all code revisions for a session",
)
async def list_revisions(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> RevisionsListResponse:
    """Retrieve full revision history and diff metrics."""
    return await service.list_revisions(session_id)


@router.get(
    "/{session_id}/timeline",
    response_model=InteractiveTimelineResponse,
    summary="Get complete interaction timeline",
)
async def list_timeline(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> InteractiveTimelineResponse:
    """Retrieve chronological log of student and TRACE interaction turns."""
    return await service.list_timeline(session_id)

