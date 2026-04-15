"""Span extraction and lexical claim-tier assignment for semantic drift."""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable

from contracts.claim_strength import (
    BOUNDARY_MARKERS,
    CAUSALITY_MARKERS,
    CLAIM_TIER_MARKERS,
    HARD_FAIL_MARKERS,
    SCOPE_MARKERS,
    STATUS_CEILINGS,
)

_WORD_CACHE: dict[str, re.Pattern[str]] = {}


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    cached = _WORD_CACHE.get(phrase)
    if cached is not None:
        return cached
    escaped = re.escape(phrase)
    if phrase.isalpha():
        pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    else:
        pattern = re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)
    _WORD_CACHE[phrase] = pattern
    return pattern


def contains_phrase(text: str, phrase: str) -> bool:
    return bool(_phrase_pattern(phrase).search(text))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def segment_claim_spans(text: str) -> list[str]:
    if not text.strip():
        return []
    spans: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        block = " ".join(part.strip() for part in paragraph if part.strip())
        paragraph.clear()
        if not block:
            return
        sentence_parts = re.split(r"(?<=[.!?])\s+|;\s+", block)
        for part in sentence_parts:
            stripped = part.strip()
            if stripped:
                spans.append(stripped)

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            continue
        if re.match(r"^#{1,6}\s+", stripped):
            flush_paragraph()
            spans.append(re.sub(r"^#{1,6}\s+", "", stripped))
            continue
        if "|" in stripped and stripped.count("|") >= 2:
            flush_paragraph()
            for cell in [cell.strip() for cell in stripped.split("|")]:
                if cell:
                    spans.append(cell)
            continue
        if re.match(r"^\s*[-*]\s+", stripped):
            flush_paragraph()
            spans.append(re.sub(r"^\s*[-*]\s+", "", stripped))
            continue
        if re.match(r"^\s*[\w.-]+\s*:\s*", stripped):
            flush_paragraph()
            spans.append(stripped)
            continue
        paragraph.append(stripped)

    flush_paragraph()
    return spans


def is_claim_bearing_span(span: str) -> bool:
    lowered = span.lower()
    if not lowered:
        return False
    if lowered.startswith("quote:"):
        return False
    for marker_group in (
        BOUNDARY_MARKERS,
        HARD_FAIL_MARKERS,
        tuple(marker for markers in CLAIM_TIER_MARKERS.values() for marker in markers),
        tuple(marker for markers in SCOPE_MARKERS.values() for marker in markers),
        tuple(marker for markers in CAUSALITY_MARKERS.values() for marker in markers),
        tuple(STATUS_CEILINGS),
        ("evidence:", "evidence_id:", "evidence_ids:", "linked_evidence:", "external validation"),
    ):
        if any(contains_phrase(lowered, marker) for marker in marker_group):
            return True
    return False


def assign_tier(span: str) -> int:
    lowered = span.lower()
    for tier in sorted(CLAIM_TIER_MARKERS, reverse=True):
        markers = CLAIM_TIER_MARKERS[tier]
        if markers and any(contains_phrase(lowered, marker) for marker in markers):
            return tier
    return 0


def extract_boundary_markers(span: str) -> tuple[str, ...]:
    lowered = span.lower()
    found = [marker for marker in BOUNDARY_MARKERS if contains_phrase(lowered, marker)]
    return tuple(sorted(found))


def classify_scope(span: str) -> int:
    lowered = span.lower()
    for level in sorted(SCOPE_MARKERS, reverse=True):
        markers = SCOPE_MARKERS[level]
        if markers and any(contains_phrase(lowered, marker) for marker in markers):
            return level
    return 0


def classify_causality(span: str) -> int:
    lowered = span.lower()
    for level in sorted(CAUSALITY_MARKERS, reverse=True):
        markers = CAUSALITY_MARKERS[level]
        if markers and any(contains_phrase(lowered, marker) for marker in markers):
            return level
    return 0


def extract_linked_evidence_ids(span: str) -> tuple[str, ...]:
    ids: list[str] = []
    patterns = (
        re.compile(
            r"\b(?:evidence|evidence_id|evidence_ids|linked_evidence|linked_evidence_ids)\s*[:=]\s*([^\n]+)",
            re.IGNORECASE,
        ),
        re.compile(r"\[evidence:\s*([^\]]+)\]", re.IGNORECASE),
    )
    for pattern in patterns:
        for match in pattern.finditer(span):
            chunk = match.group(1)
            for part in re.split(r"[\s,\[\]]+", chunk):
                token = part.strip().strip("'\"")
                if token and re.match(r"^[A-Za-z0-9_.:-]+$", token):
                    ids.append(token)
    unique: list[str] = []
    seen: set[str] = set()
    for token in ids:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return tuple(unique)


def extract_inline_claim_status(span: str) -> str:
    match = re.search(
        r"(?im)^\s*(?:claim_status|status|p_status|status_of_claim)\s*:\s*[`'\"]?([a-z_]+)[`'\"]?\s*$",
        span,
    )
    if match:
        return match.group(1).strip().lower()
    return ""


def align_claim_spans(before: str, after: str) -> list[tuple[str, str]]:
    before_spans = [span for span in segment_claim_spans(before) if is_claim_bearing_span(span)]
    after_spans = [span for span in segment_claim_spans(after) if is_claim_bearing_span(span)]

    matcher = difflib.SequenceMatcher(
        a=[normalize_text(span) for span in before_spans],
        b=[normalize_text(span) for span in after_spans],
        autojunk=False,
    )
    aligned: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        before_chunk = before_spans[i1:i2]
        after_chunk = after_spans[j1:j2]
        chunk_len = max(len(before_chunk), len(after_chunk))
        for index in range(chunk_len):
            left = before_chunk[index] if index < len(before_chunk) else ""
            right = after_chunk[index] if index < len(after_chunk) else ""
            aligned.append((left, right))
    return aligned


def iter_claim_spans(texts: Iterable[str]) -> list[str]:
    spans: list[str] = []
    for text in texts:
        spans.extend(segment_claim_spans(text))
    return [span for span in spans if is_claim_bearing_span(span)]
