"""
DocuMind AI - Phase 5: Rule-based document structure detection.

Reads cleaned text (from text_cleaner.py) and detects basic
structural elements - headings, paragraphs, bullet lists, and
numbered lists - using simple rules only. No AI/LLM involved.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STRUCTURE_DIR = BASE_DIR / "structure"
STRUCTURE_DIR.mkdir(exist_ok=True)

_BULLET_LINE = re.compile(r"^\s*[-*•‣·]\s+(.*)$")
_NUMBERED_LINE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_HEADING_END_CHARS = tuple(".!?:;")
_HEADING_MAX_WORDS = 10


def _classify_line(line: str):
    """Return (element_type, text) for a single line - bullet, numbered_item, or None."""
    bullet_match = _BULLET_LINE.match(line)
    if bullet_match:
        return "bullet", bullet_match.group(1).strip()

    numbered_match = _NUMBERED_LINE.match(line)
    if numbered_match:
        return "numbered_item", numbered_match.group(1).strip()

    return None, line


def _looks_like_heading(line: str) -> bool:
    """Short line, no terminal punctuation - a simple, conservative heading signal."""
    if line.endswith(_HEADING_END_CHARS):
        return False
    word_count = len(line.split())
    return 0 < word_count <= _HEADING_MAX_WORDS


def _detect_block_elements(block_text: str) -> list:
    """
    Classify one cleaned block (a group of lines with no blank line between
    them) into one or more elements. Bullets and numbered items are always
    their own element; consecutive plain lines are grouped into a paragraph
    (or a heading, if that group is just one short, unpunctuated line).
    """
    lines = [line for line in block_text.split("\n") if line.strip()]
    if not lines:
        return []

    elements = []
    plain_lines = []

    def flush_plain_lines():
        if not plain_lines:
            return
        if len(plain_lines) == 1 and _looks_like_heading(plain_lines[0]):
            elements.append({"element_type": "heading", "text": plain_lines[0]})
        else:
            elements.append({"element_type": "paragraph", "text": " ".join(plain_lines)})
        plain_lines.clear()

    for line in lines:
        line_type, text = _classify_line(line)
        if line_type in ("bullet", "numbered_item"):
            flush_plain_lines()
            elements.append({"element_type": line_type, "text": text})
        else:
            plain_lines.append(line)

    flush_plain_lines()
    return elements


def _detect_page_elements(page_text: str) -> list:
    """Split a page's cleaned text into blocks (blank-line separated) and classify each."""
    blocks = [b for b in page_text.split("\n\n") if b.strip()]
    elements = []
    for block in blocks:
        elements.extend(_detect_block_elements(block))
    return elements


def structure_document(document_id: str, cleaned: dict) -> dict:
    """
    Detect structure from a cleaned-text result (as produced by
    text_cleaner.clean_document) and save it to structure/{document_id}.json.
    """
    filename = cleaned.get("filename")
    document_type = cleaned.get("document_type")

    try:
        if cleaned.get("pages"):
            pages = [
                {"page_number": page["page_number"], "elements": _detect_page_elements(page["text"])}
                for page in cleaned["pages"]
            ]
        else:
            pages = [{"page_number": None, "elements": _detect_page_elements(cleaned.get("text", ""))}]
    except Exception:
        result = _build_result(
            document_id, filename, document_type, status="structure_failed",
            error="Could not detect structure for this document.",
        )
        _save_structure(document_id, result)
        return result

    # Every element remembers the nearest heading before it (its "section"),
    # carried across page boundaries since a section doesn't reset at a page break.
    current_section = None
    section_count = 0
    element_count = 0
    for page in pages:
        for element in page["elements"]:
            if element["element_type"] == "heading":
                current_section = element["text"]
                section_count += 1
            element["section"] = current_section
            element_count += 1

    if element_count == 0:
        result = _build_result(
            document_id, filename, document_type, status="structure_failed",
            error="No structural elements were found in this document.",
        )
        _save_structure(document_id, result)
        return result

    result = _build_result(
        document_id, filename, document_type, status="structured",
        pages=pages, section_count=section_count, element_count=element_count,
    )
    _save_structure(document_id, result)
    return result


def _build_result(document_id, filename, document_type, status, pages=None,
                   section_count=0, element_count=0, error=None) -> dict:
    return {
        "document_id": document_id,
        "filename": filename,
        "document_type": document_type,
        "status": status,
        "pages": pages,
        "section_count": section_count,
        "element_count": element_count,
        "error": error,
        "structured_at": datetime.now(timezone.utc).isoformat(),
    }


def _save_structure(document_id: str, result: dict) -> None:
    path = STRUCTURE_DIR / f"{document_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def load_structure(document_id: str):
    """Load a previously saved structure result, or None if it doesn't exist."""
    path = STRUCTURE_DIR / f"{document_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_structure(document_id: str) -> None:
    """Remove a saved structure result, if any."""
    path = STRUCTURE_DIR / f"{document_id}.json"
    if path.exists():
        path.unlink()