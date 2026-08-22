"""
DocuMind AI - Phase 7: Document statistics.

Calculates basic counts (characters, words, sentences, paragraphs,
pages, sections, headings, list items) from a document's cleaned
text (Phase 4) and detected structure (Phase 5). Reads only - never
modifies the cleaned text or structure data.
"""

import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _count_sentences(text: str) -> int:
    """Split on sentence-ending punctuation followed by whitespace."""
    text = text.strip()
    if not text:
        return 0
    parts = _SENTENCE_SPLIT.split(text)
    return len([p for p in parts if p.strip()])


def calculate_statistics(document_id: str, cleaned: dict, structure: dict) -> dict:
    """
    Compute document statistics.
    Character/word/sentence counts come from the cleaned text; page,
    section, heading, paragraph, and list-item counts come from the
    detected structure, since that's where those elements are classified.
    """
    text = cleaned.get("text", "")

    character_count = len(text)
    word_count = len(text.split())
    sentence_count = _count_sentences(text)

    pages = structure.get("pages") or []
    page_count = len(pages)

    heading_count = 0
    paragraph_count = 0
    list_item_count = 0

    for page in pages:
        for element in page["elements"]:
            element_type = element["element_type"]
            if element_type == "heading":
                heading_count += 1
            elif element_type == "paragraph":
                paragraph_count += 1
            elif element_type in ("bullet", "numbered_item"):
                list_item_count += 1

    return {
        "document_id": document_id,
        "character_count": character_count,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "page_count": page_count,
        "section_count": structure.get("section_count", 0),
        "heading_count": heading_count,
        "list_item_count": list_item_count,
    }