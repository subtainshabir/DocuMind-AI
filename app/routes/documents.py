"""
DocuMind AI - Document API routes.

Phase 2: upload / list / get / delete.
Phase 3: extract text from a stored document, and fetch extracted text.
Phase 4: clean extracted text, and fetch cleaned text.
Phase 5: detect document structure from cleaned text, and fetch it.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.document_extractor import extract_document, load_extracted
from app.services.document_store import (
    UPLOAD_DIR,
    delete_document,
    get_document,
    list_documents,
    save_document,
    update_document_metadata,
)
from app.services.structure_detector import load_structure, structure_document
from app.services.text_cleaner import clean_document, load_cleaned

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
    """Delete an uploaded document's file, metadata, extracted text, and cleaned text."""
    delete_document(document_id)
    return {"status": "deleted", "document_id": document_id}


@router.post("/{document_id}/extract")
def extract_document_text(document_id: str):
    """Extract text from an already-uploaded document and store the result."""
    document = get_document(document_id)

    stored_path = UPLOAD_DIR / document["stored_filename"]
    if not stored_path.exists():
        update_document_metadata(
            document_id,
            extraction_status="extraction_failed",
            extraction_error="Stored file is missing on the server.",
        )
        raise HTTPException(status_code=404, detail="Stored file is missing on the server.")

    update_document_metadata(document_id, extraction_status="extracting")

    result = extract_document(
        document_id=document_id,
        stored_path=stored_path,
        extension=document["extension"],
        filename=document["original_filename"],
    )

    update_document_metadata(
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
    """Return previously extracted (raw) text for a document, if any exists."""
    get_document(document_id)  # 404s if the document itself doesn't exist

    extracted = load_extracted(document_id)
    if not extracted:
        raise HTTPException(status_code=404, detail="This document has not been extracted yet.")

    return extracted


@router.post("/{document_id}/clean")
def clean_document_text(document_id: str):
    """Clean a document's raw extracted text and store the cleaned result."""
    document = get_document(document_id)

    if document.get("extraction_status") != "extracted":
        raise HTTPException(
            status_code=400,
            detail="This document must be successfully extracted before it can be cleaned.",
        )

    extracted = load_extracted(document_id)
    if not extracted:
        raise HTTPException(status_code=404, detail="Raw extracted text is missing for this document.")

    update_document_metadata(document_id, cleaning_status="cleaning")

    # Always clean from the raw extracted text, never from a previous cleaned
    # result - this keeps re-cleaning idempotent instead of compounding.
    result = clean_document(document_id, extracted)

    update_document_metadata(
        document_id,
        cleaning_status=result["status"],
        cleaning_timestamp=result["cleaned_at"],
        cleaned_character_count=result["character_count"],
        cleaned_word_count=result["word_count"],
        cleaning_error=result["error"],
    )

    if result["status"] == "cleaning_failed":
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@router.get("/{document_id}/cleaned-text")
def get_document_cleaned_text(document_id: str):
    """Return previously cleaned text for a document, if any exists."""
    get_document(document_id)  # 404s if the document itself doesn't exist

    cleaned = load_cleaned(document_id)
    if not cleaned:
        raise HTTPException(status_code=404, detail="This document has not been cleaned yet.")

    return cleaned


@router.post("/{document_id}/structure")
def detect_document_structure(document_id: str):
    """Detect basic structure (headings/paragraphs/lists) from a document's cleaned text."""
    document = get_document(document_id)

    if document.get("cleaning_status") != "cleaned":
        raise HTTPException(
            status_code=400,
            detail="This document must be successfully cleaned before its structure can be detected.",
        )

    cleaned = load_cleaned(document_id)
    if not cleaned:
        raise HTTPException(status_code=404, detail="Cleaned text is missing for this document.")

    update_document_metadata(document_id, structure_status="detecting")

    # Always detect from the cleaned text, never from a previous structure
    # result - this keeps re-detection idempotent instead of compounding.
    result = structure_document(document_id, cleaned)

    update_document_metadata(
        document_id,
        structure_status=result["status"],
        structure_timestamp=result["structured_at"],
        section_count=result["section_count"],
        structure_error=result["error"],
    )

    if result["status"] == "structure_failed":
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@router.get("/{document_id}/structure")
def get_document_structure(document_id: str):
    """Return previously detected structure for a document, if any exists."""
    get_document(document_id)  # 404s if the document itself doesn't exist

    structure = load_structure(document_id)
    if not structure:
        raise HTTPException(status_code=404, detail="This document's structure has not been detected yet.")

    return structure