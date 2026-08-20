"""
DocuMind AI - Phase 4: Text cleaning and normalization.

Turns raw extracted text (from document_extractor.py) into a
cleaner, more consistent representation - conservatively, without
discarding meaning, paragraph structure, page boundaries, or
Unicode content. Saves the result separately from the raw text.
"""

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLEANED_DIR = BASE_DIR / "cleaned"
CLEANED_DIR.mkdir(exist_ok=True)

_BULLET_PREFIX = re.compile(r"^(\s*)([-*•‣·]|\d+[.)])\s+")
_SENTENCE_END_CHARS = tuple(".!?:;)]}\"'”’")


def _normalize_line_endings(text: str) -> str:
    """Convert Windows (CRLF) and old Mac (CR) line endings to plain \\n."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _strip_control_characters(text: str) -> str:
    """Drop unprintable control characters, but keep newlines/tabs and all Unicode letters."""
    return "".join(
        ch for ch in text
        if ch in ("\n", "\t") or unicodedata.category(ch) != "Cc"
    )


def _normalize_whitespace(line: str) -> str:
    """Collapse runs of spaces/tabs into one space and trim the line's edges."""
    line = line.replace("\xa0", " ")
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def _is_structural_line(line: str) -> bool:
    """Bullet points and numbered list items are never merged into a paragraph."""
    return bool(_BULLET_PREFIX.match(line))


def _should_join(current: str, nxt: str) -> bool:
    """
    Conservative check: only join two lines when the first clearly does not
    end a sentence. Bullets/numbered items are never merged into a paragraph,
    which is what keeps this from collapsing genuine paragraph breaks.
    """
    if not current or not nxt:
        return False
    if _is_structural_line(current) or _is_structural_line(nxt):
        return False
    return not current.endswith(_SENTENCE_END_CHARS)


def _join_pair(current: str, nxt: str) -> str:
    """Join a wrapped line into the next, repairing an obvious line-break hyphen."""
    if len(current) >= 2 and current[-1] == "-" and current[-2].isalpha() and nxt[0].islower():
        return current[:-1] + nxt
    return current + " " + nxt


def _clean_block(lines: list) -> str:
    """Repair line-wrapping inside one paragraph/list block, line by line."""
    lines = [_normalize_whitespace(line) for line in lines]
    lines = [line for line in lines if line]
    if not lines:
        return ""

    joined = [lines[0]]
    for line in lines[1:]:
        if _should_join(joined[-1], line):
            joined[-1] = _join_pair(joined[-1], line)
        else:
            joined.append(line)
    return "\n".join(joined)


def _clean_text_block(text: str) -> str:
    """Clean one piece of text (a page, or a whole document)."""
    text = _normalize_line_endings(text)
    text = _strip_control_characters(text)

    blocks = []
    current_block = []

    for line in text.split("\n"):
        if _normalize_whitespace(line):
            current_block.append(line)
        elif current_block:
            blocks.append(_clean_block(current_block))
            current_block = []

    if current_block:
        blocks.append(_clean_block(current_block))

    return "\n\n".join(block for block in blocks if block)


def clean_document(document_id: str, extracted: dict) -> dict:
    """
    Clean a raw extraction result (as produced by document_extractor.extract_document)
    and save the cleaned representation to cleaned/{document_id}.json.
    """
    filename = extracted.get("filename")
    document_type = extracted.get("document_type")

    try:
        if extracted.get("pages"):
            cleaned_pages = [
                {"page_number": page["page_number"], "text": _clean_text_block(page["text"])}
                for page in extracted["pages"]
            ]
            cleaned_text = "\n\n".join(p["text"] for p in cleaned_pages if p["text"])
        else:
            cleaned_pages = None
            cleaned_text = _clean_text_block(extracted.get("text", ""))
    except Exception:
        result = _build_result(
            document_id, filename, document_type, status="cleaning_failed",
            error="Could not clean this document's text.",
        )
        _save_cleaned(document_id, result)
        return result

    if not cleaned_text.strip():
        result = _build_result(
            document_id, filename, document_type, status="cleaning_failed",
            error="No cleanable text was found.",
        )
        _save_cleaned(document_id, result)
        return result

    result = _build_result(
        document_id, filename, document_type, status="cleaned",
        text=cleaned_text, pages=cleaned_pages,
        character_count=len(cleaned_text), word_count=len(cleaned_text.split()),
        original_character_count=extracted.get("character_count"),
    )
    _save_cleaned(document_id, result)
    return result


def _build_result(document_id, filename, document_type, status, text="", pages=None,
                   character_count=0, word_count=0, original_character_count=None, error=None) -> dict:
    return {
        "document_id": document_id,
        "filename": filename,
        "document_type": document_type,
        "status": status,
        "text": text,
        "pages": pages,
        "character_count": character_count,
        "word_count": word_count,
        "original_character_count": original_character_count,
        "error": error,
        "cleaned_at": datetime.now(timezone.utc).isoformat(),
    }


def _save_cleaned(document_id: str, result: dict) -> None:
    path = CLEANED_DIR / f"{document_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def load_cleaned(document_id: str):
    """Load a previously saved cleaning result, or None if it doesn't exist."""
    path = CLEANED_DIR / f"{document_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_cleaned(document_id: str) -> None:
    """Remove a saved cleaning result, if any."""
    path = CLEANED_DIR / f"{document_id}.json"
    if path.exists():
        path.unlink()