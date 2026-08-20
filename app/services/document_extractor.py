"""
DocuMind AI - Phase 3: Text extraction from stored documents.

Reads an already-uploaded file from disk and extracts its raw text.
This module does NOT clean, chunk, or embed anything - its only job
is: stored file -> extracted text -> saved separately on disk.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import fitz
from docx import Document as DocxDocument

BASE_DIR = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = BASE_DIR / "extracted"
EXTRACTED_DIR.mkdir(exist_ok=True)


def _extract_pdf(path: Path) -> dict:
    """Extract text page by page from a PDF using PyMuPDF."""
    pdf = fitz.open(str(path))
    pages = []
    try:
        for page_number in range(len(pdf)):
            page = pdf.load_page(page_number)
            page_text = page.get_text().strip()
            pages.append({"page_number": page_number + 1, "text": page_text})
    finally:
        pdf.close()

    full_text = "\n\n".join(p["text"] for p in pages if p["text"])
    return {"text": full_text, "pages": pages, "page_count": len(pages)}


def _extract_docx(path: Path) -> dict:
    """Extract paragraph text, in order, from a DOCX file using python-docx."""
    document = DocxDocument(str(path))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)
    return {"text": full_text, "pages": None, "page_count": None}


def _extract_txt(path: Path) -> dict:
    """Read a TXT file as UTF-8, falling back to Latin-1 if that fails."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    return {"text": text, "pages": None, "page_count": None}


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".txt": _extract_txt,
}


def extract_document(document_id: str, stored_path: Path, extension: str, filename: str) -> dict:
    """
    Extract text from a stored file and save the result to extracted/{id}.json.
    Returns the same result dict that gets saved to disk.
    """
    extractor = _EXTRACTORS.get(extension)

    if extractor is None:
        result = _build_result(
            document_id, filename, extension, status="extraction_failed",
            error=f"Unsupported file type for extraction: {extension}",
        )
        _save_extracted(document_id, result)
        return result

    try:
        extracted = extractor(stored_path)
    except Exception:
        result = _build_result(
            document_id, filename, extension, status="extraction_failed",
            error=f"Could not read this {extension} file. It may be corrupted.",
        )
        _save_extracted(document_id, result)
        return result

    text = extracted["text"].strip()

    if not text:
        result = _build_result(
            document_id, filename, extension, status="extraction_failed",
            error="No extractable text was found in this document.",
            page_count=extracted.get("page_count"),
        )
        _save_extracted(document_id, result)
        return result

    result = _build_result(
        document_id, filename, extension, status="extracted",
        text=text, pages=extracted.get("pages"), page_count=extracted.get("page_count"),
        character_count=len(text),
    )
    _save_extracted(document_id, result)
    return result


def _build_result(document_id, filename, extension, status, text="", pages=None,
                   page_count=None, character_count=0, error=None) -> dict:
    return {
        "document_id": document_id,
        "filename": filename,
        "document_type": extension,
        "status": status,
        "text": text,
        "pages": pages,
        "page_count": page_count,
        "character_count": character_count,
        "error": error,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }


def _save_extracted(document_id: str, result: dict) -> None:
    path = EXTRACTED_DIR / f"{document_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def load_extracted(document_id: str):
    """Load a previously saved extraction result, or None if it doesn't exist."""
    path = EXTRACTED_DIR / f"{document_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_extracted(document_id: str) -> None:
    """Remove a saved extraction result, if any."""
    path = EXTRACTED_DIR / f"{document_id}.json"
    if path.exists():
        path.unlink()