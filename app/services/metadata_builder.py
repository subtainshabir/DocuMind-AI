"""
DocuMind AI - Phase 6: Page & section metadata.

Takes a document's detected structure (from structure_detector.py) and
flattens it into a simple, linear list of content records - each one
tagged with its document, page, section, type, and position - plus a
separate list of the document's sections in order. This is what future
chunking/RAG phases will attach to each chunk for citations and filtering.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
METADATA_DIR = BASE_DIR / "metadata"
METADATA_DIR.mkdir(exist_ok=True)


def build_metadata(document_id: str, structure: dict) -> dict:
    """
    Flatten a structure result (as produced by structure_detector.structure_document)
    into per-element and per-section metadata, and save it to metadata/{document_id}.json.
    """
    filename = structure.get("filename")

    elements = []
    sections = []
    position = 0
    section_order = 0

    for page in structure.get("pages") or []:
        page_number = page["page_number"]
        for element in page["elements"]:
            elements.append({
                "document_id": document_id,
                "filename": filename,
                "page_number": page_number,
                "section": element.get("section"),
                "element_type": element["element_type"],
                "text": element["text"],
                "position": position,
            })
            position += 1

            if element["element_type"] == "heading":
                sections.append({
                    "section": element["text"],
                    "page_number": page_number,
                    "section_order": section_order,
                })
                section_order += 1

    result = {
        "document_id": document_id,
        "filename": filename,
        "elements": elements,
        "sections": sections,
        "element_count": len(elements),
        "section_count": len(sections),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    _save_metadata(document_id, result)
    return result


def _save_metadata(document_id: str, result: dict) -> None:
    path = METADATA_DIR / f"{document_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def load_metadata(document_id: str):
    """Load previously built page/section metadata, or None if it doesn't exist."""
    path = METADATA_DIR / f"{document_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_metadata(document_id: str) -> None:
    """Remove saved page/section metadata, if any."""
    path = METADATA_DIR / f"{document_id}.json"
    if path.exists():
        path.unlink()