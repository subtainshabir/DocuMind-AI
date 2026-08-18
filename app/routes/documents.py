"""
DocuMind AI - Document API routes.

Phase 2: upload / list / get / delete.
Phase 3: extract text from a stored document, and fetch extracted text.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.document_extractor import extract_document, load_extracted
from app.services.document_store import (
    UPLOAD_DIR,
    delete_document,
    get_document,
    list_documents,
    save_document,
    update_extraction_metadata,
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
    """Delete an uploaded document's file, metadata, and any extracted text."""
    delete_document(document_id)
    return {"status": "deleted", "document_id": document_id}


@router.post("/{document_id}/extract")
def extract_document_text(document_id: str):
    """Extract text from an already-uploaded document and store the result."""
    document = get_document(document_id)

    stored_path = UPLOAD_DIR / document["stored_filename"]
    if not stored_path.exists():
        update_extraction_metadata(
            document_id,
            extraction_status="extraction_failed",
            extraction_error="Stored file is missing on the server.",
        )
        raise HTTPException(status_code=404, detail="Stored file is missing on the server.")

    update_extraction_metadata(document_id, extraction_status="extracting")

    result = extract_document(
        document_id=document_id,
        stored_path=stored_path,
        extension=document["extension"],
        filename=document["original_filename"],
    )

    update_extraction_metadata(
        document_id,
        extraction_status=result["status"],
        extraction_timestamp=result["extracted_at"],
        character_count=result["character_count"],
        page_count=result["page_count"],
        extraction_error=result["error"],
    )

    if result["status"] == "extraction_failed":
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@router.get("/{document_id}/text")
def get_document_text(document_id: str):
    """Return previously extracted text for a document, if any exists."""
    get_document(document_id)  # 404s if the document itself doesn't exist

    extracted = load_extracted(document_id)
    if not extracted:
        raise HTTPException(status_code=404, detail="This document has not been extracted yet.")

    return extracted