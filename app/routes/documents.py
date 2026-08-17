"""
DocuMind AI - Phase 2: Document upload/list/delete API routes.
"""

from fastapi import APIRouter, File, UploadFile

from app.services.document_store import (
    delete_document,
    get_document,
    list_documents,
    save_document,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF, DOCX, or TXT file. Validates, stores it, and returns its metadata."""
    return await save_document(file)


@router.get("/")
def get_documents():
    """List metadata for all uploaded documents."""
    return list_documents()


@router.get("/{document_id}")
def get_one_document(document_id: str):
    """Get metadata for a single uploaded document."""
    return get_document(document_id)


@router.delete("/{document_id}")
def remove_document(document_id: str):
    """Delete an uploaded document's file and metadata."""
    delete_document(document_id)
    return {"status": "deleted", "document_id": document_id}