from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List
import os
import uuid

from app.auth.models import CurrentUser
from app.auth.dependencies import get_current_user, get_db
from app.services.document_service import DocumentService
from app.services.vector_service import VectorService
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_doc_service() -> DocumentService:
    return DocumentService(
        upload_dir=settings.UPLOAD_DIR,
        docling_serve_url=settings.DOCLING_SERVE_URL,
    )


def _get_vector_service() -> VectorService:
    return VectorService(
        persist_directory=settings.VECTOR_DB_PATH,
        api_key=settings.OPENAI_API_KEY,
    )


@router.post("/upload/{project_id}")
async def upload_documents(
    project_id: str,
    files: List[UploadFile] = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    db = get_db()

    # Verify project ownership
    project = db.get_project(project_id)
    if not project or project["owner_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    doc_service = _get_doc_service()
    vector_service = _get_vector_service()

    results = []
    for file in files:
        # Save file to disk
        doc_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        save_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{file_ext}")
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        try:
            # Parse and chunk
            doc_result = await doc_service.process_document(save_path, file.filename, doc_id=doc_id)

            # Embed chunks in ChromaDB
            if doc_result["chunks"]:
                await vector_service.add_documents(project_id, doc_result["chunks"])

            # Save metadata to SQLite
            file_type = doc_service.get_file_type(file.filename)
            doc_record = db.save_document(
                doc_id=doc_id,
                project_id=project_id,
                filename=file.filename,
                file_path=save_path,
                file_type=file_type,
                total_pages=doc_result["metadata"]["total_pages"],
                total_chunks=doc_result["metadata"]["total_chunks"],
                cached_markdown=doc_result.get("cached_markdown"),
            )

            results.append({
                "doc_id": doc_id,
                "filename": file.filename,
                "total_pages": doc_result["metadata"]["total_pages"],
                "total_chunks": doc_result["metadata"]["total_chunks"],
                "status": "success",
            })
        except Exception as e:
            # Clean up file on failure
            if os.path.exists(save_path):
                os.remove(save_path)
            results.append({
                "doc_id": doc_id,
                "filename": file.filename,
                "status": "error",
                "error": str(e),
            })

    return {"documents": results}


@router.get("/{project_id}")
async def list_documents(project_id: str, current_user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    project = db.get_project(project_id)
    if not project or project["owner_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = db.get_documents_by_project(project_id)
    return {"documents": docs}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, current_user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify ownership via project
    project = db.get_project(doc["project_id"])
    if not project or project["owner_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete vectors
    vector_service = _get_vector_service()
    vector_service.delete_document_chunks(doc["project_id"], doc_id)

    # Delete file from disk
    if os.path.exists(doc["file_path"]):
        os.remove(doc["file_path"])

    # Delete from DB
    db.delete_document(doc_id)
    return {"detail": "Document deleted"}
