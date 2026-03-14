import httpx
from typing import List, Dict, Optional, Tuple
import os
import uuid
import asyncio
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentConversionError(Exception):
    """Raised when Docling Serve fails to convert a document"""
    pass


class PasswordProtectedError(Exception):
    """Raised when a document is password protected"""
    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(f"Document '{filename}' is password protected")


class DocumentService:
    """Service for processing documents via Docling Serve HTTP API"""

    def __init__(self, upload_dir: str = "data/uploads", docling_serve_url: str = ""):
        self.upload_dir = upload_dir
        self.docling_serve_url = docling_serve_url.rstrip("/")
        os.makedirs(upload_dir, exist_ok=True)

    async def process_document(self, file_path: str, filename: str, doc_id: Optional[str] = None) -> Dict:
        """
        Process document via Docling Serve and extract structured chunks.

        Sends file to Docling Serve /v1/convert/file, gets markdown back,
        then chunks it locally.
        """
        # Calculate file hash for duplicate detection
        file_hash = await asyncio.to_thread(self._calculate_file_hash, file_path)

        # Get file timestamps
        file_stats = os.stat(file_path)
        file_created_at = datetime.fromtimestamp(file_stats.st_ctime).isoformat()
        file_modified_at = datetime.fromtimestamp(file_stats.st_mtime).isoformat()

        ext = os.path.splitext(file_path)[1].lower()

        # TXT files — read directly, no need for Docling
        if ext == '.txt':
            return await self._process_txt_file(file_path, filename, doc_id)

        # Send to Docling Serve
        full_text, num_pages = await self._convert_via_docling_serve(file_path, filename)

        # Use provided doc_id or generate new one
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        chunks = []

        # Split text into chunks
        if full_text:
            text_chunks = self.chunk_text(full_text, chunk_size=3000, overlap=300)
            for i, chunk_text in enumerate(text_chunks):
                estimated_page = int((i * 800) / 3000) + 1 if num_pages > 0 else None

                chunk = {
                    'id': str(uuid.uuid4()),
                    'doc_id': doc_id,
                    'doc_name': filename,
                    'content': chunk_text,
                    'page': estimated_page if estimated_page and estimated_page <= num_pages else None,
                }
                chunks.append(chunk)

        return {
            'doc_id': doc_id,
            'filename': filename,
            'chunks': chunks,
            'metadata': {
                'total_pages': num_pages,
                'total_chunks': len(chunks)
            },
            'file_hash': file_hash,
            'file_created_at': file_created_at,
            'file_modified_at': file_modified_at,
            'cached_markdown': full_text
        }

    async def _convert_via_docling_serve(self, file_path: str, filename: str) -> Tuple[str, int]:
        """
        Call Docling Serve /v1/convert/file endpoint.

        Returns:
            Tuple of (markdown_text, num_pages)
        """
        url = f"{self.docling_serve_url}/v1/convert/file"

        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(file_path, "rb") as f:
                response = await client.post(
                    url,
                    files={"files": (filename, f)},
                    data={"to_formats": ["md", "json"]},
                )

        if response.status_code != 200:
            logger.error(f"Docling Serve error {response.status_code}: {response.text[:500]}")
            raise DocumentConversionError(
                f"Docling Serve returned {response.status_code} for {filename}"
            )

        data = response.json()
        status = data.get("status")

        if status not in ("success", "partial_success"):
            errors = data.get("errors", [])
            error_msg = "; ".join(e.get("message", str(e)) for e in errors) if errors else "Unknown error"
            raise DocumentConversionError(
                f"Docling Serve conversion failed for {filename}: {error_msg}"
            )

        doc = data.get("document", {})
        md_content = doc.get("md_content", "") or ""

        # Extract num_pages from json_content
        # For PDFs: pages dict has page numbers as keys
        # For DOCX/PPTX: pages is usually empty
        num_pages = 0
        json_content = doc.get("json_content")
        if json_content and isinstance(json_content, dict):
            pages = json_content.get("pages", {})
            if isinstance(pages, dict) and pages:
                num_pages = len(pages)
            else:
                num_pages = json_content.get("num_pages", 0)

        processing_time = data.get("processing_time", 0)
        logger.info(
            f"Docling Serve converted {filename}: {len(md_content)} chars, "
            f"{num_pages} pages, {processing_time:.1f}s"
        )

        return md_content, num_pages

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for duplicate detection"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Semantic chunking with overlap"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)
        return chunks

    async def _process_txt_file(self, file_path: str, filename: str, doc_id: Optional[str] = None) -> Dict:
        """Process plain text files directly (no Docling needed)"""
        file_hash = await asyncio.to_thread(self._calculate_file_hash, file_path)

        file_stats = os.stat(file_path)
        file_created_at = datetime.fromtimestamp(file_stats.st_ctime).isoformat()
        file_modified_at = datetime.fromtimestamp(file_stats.st_mtime).isoformat()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    full_text = f.read()
            except Exception:
                with open(file_path, 'rb') as f:
                    full_text = f.read().decode('utf-8', errors='ignore')

        if doc_id is None:
            doc_id = str(uuid.uuid4())

        chunks = []
        if full_text:
            text_chunks = self.chunk_text(full_text, chunk_size=3000, overlap=300)
            for i, chunk_text in enumerate(text_chunks):
                chunk = {
                    'id': str(uuid.uuid4()),
                    'doc_id': doc_id,
                    'doc_name': filename,
                    'content': chunk_text,
                    'page': None,
                }
                chunks.append(chunk)

        return {
            'doc_id': doc_id,
            'filename': filename,
            'chunks': chunks,
            'metadata': {
                'total_pages': 0,
                'total_chunks': len(chunks)
            },
            'file_hash': file_hash,
            'file_created_at': file_created_at,
            'file_modified_at': file_modified_at,
            'cached_markdown': full_text
        }

    def get_file_type(self, filename: str) -> str:
        """Get file type from filename"""
        ext = os.path.splitext(filename)[1].lower()
        type_map = {
            '.pdf': 'pdf', '.docx': 'docx', '.doc': 'doc',
            '.pptx': 'pptx', '.ppt': 'ppt',
            '.html': 'html', '.htm': 'html',
            '.md': 'markdown', '.asciidoc': 'asciidoc', '.adoc': 'asciidoc',
            '.txt': 'txt',
            '.csv': 'csv', '.xlsx': 'xlsx', '.xls': 'xls',
            '.png': 'image', '.jpg': 'image', '.jpeg': 'image',
            '.gif': 'image', '.bmp': 'image', '.tiff': 'image', '.tif': 'image',
            '.mp3': 'audio', '.mp4': 'audio', '.wav': 'audio', '.m4a': 'audio',
            '.vtt': 'vtt', '.xml': 'xml', '.json': 'json',
        }
        return type_map.get(ext, 'unknown')

    def is_pdf_password_protected(self, file_path: str) -> bool:
        """Check if a PDF file is password protected"""
        if not file_path.lower().endswith('.pdf'):
            return False
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            return reader.is_encrypted
        except Exception as e:
            logger.warning(f"Error checking PDF encryption: {e}")
            return False
