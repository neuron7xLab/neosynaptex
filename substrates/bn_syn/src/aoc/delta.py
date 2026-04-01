from __future__ import annotations

import re
from typing import Any

from .contracts import DeltaBreakdown, TaskContract

_TOKEN_RE = re.compile(r"[^a-z0-9\s]")


def _tokens(text: str) -> list[str]:
    lowered = _TOKEN_RE.sub(" ", text.lower())
    return [tok for tok in lowered.split() if tok]


def _heading_set(content: str) -> list[str]:
    headings: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            headings.append(line[3:].strip().lower())
    return headings


class DeltaEngine:
    def compute(self, contract: TaskContract, content: str, checks: dict[str, Any]) -> DeltaBreakdown:
        required_sections = [s.lower() for s in contract.constraints["required_sections"]]

        # semantic delta = 1 - recall(required signal tokens)
        signal = set(_tokens(contract.objective))
        for section in required_sections:
            signal.update(_tokens(section))
        observed = set(_tokens(content))
        if not signal:
            raise ValueError("cannot compute semantic delta without signal tokens")
        recall = len(signal & observed) / len(signal)
        semantic = 1.0 - recall

        # structural delta from missing required headings + ordering violations
        headings = _heading_set(content)
        missing = [s for s in required_sections if s not in headings]
        missing_ratio = len(missing) / max(1, len(required_sections))
        order_violations = 0
        for idx, sec in enumerate([s for s in required_sections if s in headings]):
            if headings.index(sec) != idx:
                order_violations += 1
        order_ratio = order_violations / max(1, len(required_sections))
        structural = min(1.0, missing_ratio * 0.8 + order_ratio * 0.2)

        # functional delta from independent checks
        req_checks = [
            v for v in checks.values() if isinstance(v, dict) and v.get("required") is True
        ]
        if not req_checks:
            raise ValueError("cannot compute functional delta without required checks")
        failed = [v for v in req_checks if v.get("passed") is False]
        functional = len(failed) / len(req_checks)

        total = (
            semantic * contract.delta_weights.semantic
            + structural * contract.delta_weights.structural
            + functional * contract.delta_weights.functional
        )
        return DeltaBreakdown(
            semantic_delta=semantic,
            structural_delta=structural,
            functional_delta=functional,
            total_delta=total,
        )
