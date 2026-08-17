"""
DocuMind AI - Phase 2: Document storage and metadata handling.

This module saves uploaded files to a local uploads/ folder and
tracks their metadata in a JSON file. It does NOT read or process
file contents - that is Phase 3's job. Phase 2 only stores files
and tracks metadata: Upload -> Validate -> Store -> Track.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
METADATA_FILE = BASE_DIR / "documents_metadata.json"

UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types for Phase 2. Extend this if new formats are supported later.
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain"},
}

# Easy to change later - 20 MB limit for Phase 2.
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


def _load_metadata() -> dict:
    """Read the metadata JSON file, or return an empty store if it doesn't exist yet."""
    if not METADATA_FILE.exists():
        return {}
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_metadata(data: dict) -> None:
    """Write the metadata dict back to disk."""
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _validate_upload(filename: str, content_type: Optional[str], size: int) -> str:
    """
    Validate an uploaded file. Returns the lowercase file extension if valid,
    otherwise raises an HTTPException with a clear error message.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="No filename was provided.")

    # Only the extension is used for validation - the filename itself is
    # never used to build a filesystem path (see generated stored_filename).
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension or 'unknown'}'. Allowed types: .pdf, .docx, .txt",
        )

    if size == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"File is too large. Maximum size is {max_mb} MB.")

    # MIME check is a soft secondary check - browsers don't always send a
    # consistent content_type, so only a clear mismatch is rejected.
    allowed_mimes = ALLOWED_MIME_TYPES.get(extension, set())
    if content_type and allowed_mimes and content_type not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match its extension ({extension}).",
        )

    return extension


async def save_document(file: UploadFile) -> dict:
    """Validate, store, and track metadata for one uploaded file."""
    content = await file.read()
    extension = _validate_upload(file.filename, file.content_type, len(content))

    # The document ID is generated here, not derived from the filename, so
    # two files named report.pdf never collide or overwrite each other.
    document_id = uuid.uuid4().hex
    stored_filename = f"{document_id}{extension}"
    stored_path = UPLOAD_DIR / stored_filename

    with open(stored_path, "wb") as f:
        f.write(content)

    metadata = {
        "document_id": document_id,
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "extension": extension,
        "mime_type": file.content_type,
        "size_bytes": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "uploaded",
    }

    all_docs = _load_metadata()
    all_docs[document_id] = metadata
    _save_metadata(all_docs)

    return metadata


def list_documents() -> list:
    """Return metadata for every uploaded document, most recent first."""
    all_docs = _load_metadata()
    return sorted(all_docs.values(), key=lambda d: d["uploaded_at"], reverse=True)


def get_document(document_id: str) -> dict:
    """Return metadata for a single document, or raise 404 if it doesn't exist."""
    all_docs = _load_metadata()
    document = all_docs.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


def delete_document(document_id: str) -> None:
    """Remove a document's stored file and its metadata entry."""
    all_docs = _load_metadata()
    document = all_docs.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    stored_path = UPLOAD_DIR / document["stored_filename"]
    if stored_path.exists():
        stored_path.unlink()

    del all_docs[document_id]
    _save_metadata(all_docs)