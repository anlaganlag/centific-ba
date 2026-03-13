from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.auth.models import CurrentUser
from app.auth.dependencies import get_current_user, get_db
from app.services.db_service import DatabaseService
from app.services.vector_service import VectorService
from app.config import settings

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    created_at: str
    document_count: int = 0


def _get_vector_service() -> VectorService:
    return VectorService(
        persist_directory=settings.VECTOR_DB_PATH,
        api_key=settings.OPENAI_API_KEY,
    )


@router.post("", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, current_user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    project = db.create_project(data.name, data.description, current_user.user_id)
    return ProjectResponse(**project, document_count=0)


@router.get("", response_model=List[ProjectResponse])
async def list_projects(current_user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    projects = db.get_projects_by_owner(current_user.user_id)
    result = []
    for p in projects:
        docs = db.get_documents_by_project(p["id"])
        result.append(ProjectResponse(**p, document_count=len(docs)))
    return result


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, current_user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    project = db.get_project(project_id)
    if not project or project["owner_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    docs = db.get_documents_by_project(project_id)
    return ProjectResponse(**project, document_count=len(docs))


@router.delete("/{project_id}")
async def delete_project(project_id: str, current_user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    project = db.get_project(project_id)
    if not project or project["owner_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete vector collection
    vector_service = _get_vector_service()
    vector_service.delete_project_collection(project_id)

    # Delete from DB (cascades to documents)
    db.delete_project(project_id)
    return {"detail": "Project deleted"}
