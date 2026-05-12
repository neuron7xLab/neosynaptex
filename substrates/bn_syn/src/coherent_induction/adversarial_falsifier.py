from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FalsifierResult:
    severity: str
    failed_rule: str
    evidence: str
    suggested_fix: str
    release_blocked: bool


def run_falsifier(text: str, has_tests: bool, has_falsifier: bool) -> FalsifierResult:
    lower = text.lower()
    if "fusion" in lower or "conscious" in lower:
        return FalsifierResult("critical", "neuroclaim_overreach", text, "remove unsupported neuroclaim", True)
    if not has_tests:
        return FalsifierResult("high", "no_test_artifact", "tests missing", "add tests", True)
    if not has_falsifier:
        return FalsifierResult("high", "no_falsifier_hypothesis", "falsifier missing", "add falsifier", True)
    return FalsifierResult("low", "none", "ok", "none", False)
