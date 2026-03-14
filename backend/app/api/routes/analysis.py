from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user, get_db
from app.auth.models import CurrentUser
from app.services.db_service import DatabaseService
from app.services.analysis_service import AnalysisService
from app.services.export_service import ExportService
from app.models.analysis import (
    StartAnalysisRequest, SubmitAnswersRequest, AnalysisStatusResponse, AnalysisStatus,
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _get_analysis_service() -> AnalysisService:
    return AnalysisService(get_db())


def _ensure_project_access(project_id: str, current_user: CurrentUser) -> dict:
    db = get_db()
    project = db.get_project(project_id)
    if not project or project["owner_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/start", response_model=AnalysisStatusResponse)
async def start_analysis(
    project_id: str,
    body: StartAnalysisRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Start BA analysis chain for a project."""
    db = get_db()
    _ensure_project_access(project_id, current_user)

    # Check documents exist
    docs = db.get_documents_by_project(project_id)
    if not docs:
        raise HTTPException(status_code=400, detail="No documents uploaded for this project")

    service = _get_analysis_service()
    result = await service.start_analysis(project_id, body.mode)
    return result


@router.get("/{project_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    project_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get current analysis status and results."""
    _ensure_project_access(project_id, current_user)

    service = _get_analysis_service()
    result = service.get_status(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="No analysis session found")
    return result


@router.get("/{project_id}/sessions")
async def list_analysis_sessions(
    project_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all analysis sessions for a project, newest first."""
    _ensure_project_access(project_id, current_user)
    db = get_db()
    sessions = db.get_analysis_sessions(project_id)
    return [
        {
            "session_id": session["id"],
            "project_id": session["project_id"],
            "mode": session["mode"],
            "status": session["status"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "error_message": session.get("error_message"),
            "progress_message": session.get("progress_message"),
        }
        for session in sessions
    ]


@router.get("/{project_id}/sessions/{session_id}", response_model=AnalysisStatusResponse)
async def get_analysis_session(
    project_id: str,
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Fetch a specific historical analysis session for a project."""
    _ensure_project_access(project_id, current_user)
    db = get_db()
    session = db.get_analysis_session(session_id)
    if not session or session["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    service = _get_analysis_service()
    return service._build_response_from_session(session)


@router.post("/{project_id}/answers", response_model=AnalysisStatusResponse)
async def submit_answers(
    project_id: str,
    body: SubmitAnswersRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Submit edited interview answers and trigger story generation (guided mode)."""
    db = get_db()
    _ensure_project_access(project_id, current_user)

    # Get the latest session
    session = db.get_latest_analysis_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="No analysis session found")

    if session["status"] != AnalysisStatus.awaiting_answers.value:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not awaiting answers (status: {session['status']})"
        )

    service = _get_analysis_service()
    try:
        result = await service.submit_answers_and_generate(session["id"], body.answers)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/export")
async def export_docx(
    project_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Export analysis results as DOCX."""
    db = get_db()
    project = _ensure_project_access(project_id, current_user)

    session = db.get_latest_analysis_session(project_id)
    if not session or session["status"] != AnalysisStatus.done.value:
        raise HTTPException(status_code=400, detail="Analysis not completed yet")

    if not session.get("features_json"):
        raise HTTPException(status_code=400, detail="No features data available")

    export_service = ExportService()
    buffer = export_service.generate_docx(session["features_json"], project["name"])

    filename = f"{project['name'].replace(' ', '_')}_BA_Analysis.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
