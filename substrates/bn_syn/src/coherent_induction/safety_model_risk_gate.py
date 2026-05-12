from __future__ import annotations

import re

_BLOCKED_PATTERNS: tuple[str, ...] = (
    r"literal\s+fusion",
    r"conscious\s+llm",
    r"neurophysiological\s+synchronization",
    r"universal\s+effect",
)

_SUPERIORITY_CLAIM = re.compile(r"\b(x\s*(7|10)|7x|10x|seven\s*times|ten\s*times)\b")
_BENCHMARK_EVIDENCE = re.compile(r"\b(benchmark|ablation|control\s+group|jsonl|confidence\s+interval|p\s*value)\b")


def _normalize(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def safety_gate(text: str) -> tuple[bool, str]:
    """Fail-closed text gate for unsupported scientific claims."""
    normalized = _normalize(text)
    if not normalized:
        return False, "blocked: empty_claim"

    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, normalized):
            return False, f"blocked: {pattern}"

    if _SUPERIORITY_CLAIM.search(normalized) and not _BENCHMARK_EVIDENCE.search(normalized):
        return False, "blocked: unbenchmarked_superiority_claim"

    return True, "safe"
