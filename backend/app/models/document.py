from pydantic import BaseModel
from typing import Optional, Dict


class DocumentChunk(BaseModel):
    """Document chunk with metadata"""
    id: str
    doc_id: str
    doc_name: str
    content: str
    page: Optional[int] = None
    position: Dict = {}


class Document(BaseModel):
    """Document metadata"""
    id: str
    filename: str
    file_path: str
    file_type: str
    total_pages: int = 0
    total_chunks: int = 0
    uploaded_at: str
    project_id: Optional[str] = None
    cached_markdown: Optional[str] = None
