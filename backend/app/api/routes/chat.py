from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.auth.models import CurrentUser
from app.auth.dependencies import get_current_user, get_db
from app.services.vector_service import VectorService
from app.agents.qa_agent import answer_question, answer_question_with_history
from app.config import settings

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[dict]] = None


def _get_vector_service() -> VectorService:
    return VectorService(
        persist_directory=settings.VECTOR_DB_PATH,
        api_key=settings.OPENAI_API_KEY,
    )


@router.post("/{project_id}")
async def ask_question(
    project_id: str,
    data: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    project = db.get_project(project_id)
    if not project or project["owner_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get relevant chunks via vector search
    vector_service = _get_vector_service()
    chunks = await vector_service.query(project_id, data.question, n_results=5)

    if not chunks:
        return {
            "answer": "No documents found in this project. Please upload documents first.",
            "sources": [],
            "confidence": 0.0,
        }

    # Call QA agent
    if data.history:
        response = await answer_question_with_history(data.question, chunks, data.history)
    else:
        response = await answer_question(data.question, chunks)

    return {
        "answer": response.answer,
        "sources": response.sources,
        "confidence": response.confidence,
        "requires_clarification": response.requires_clarification,
        "clarification_question": response.clarification_question,
    }
