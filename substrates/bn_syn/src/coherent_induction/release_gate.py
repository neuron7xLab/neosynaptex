from __future__ import annotations

import json
from pathlib import Path


_REQUIRED_GROUPS: tuple[str, str] = ("A", "D")


def _validated_multiplier(thresholds: dict[str, float]) -> float:
    multiplier = float(thresholds["artifact_quality_multiplier"])
    if multiplier <= 0.0:
        raise ValueError("artifact_quality_multiplier must be > 0")
    return multiplier


def evaluate_ten_x(results_path: Path, thresholds: dict[str, float]) -> dict[str, object]:
    rows = [json.loads(line) for line in results_path.read_text().splitlines() if line.strip()]
    groups = {row["group"]: row for row in rows}

    missing = [group for group in _REQUIRED_GROUPS if group not in groups]
    if missing:
        return {"verdict": "FAIL", "reason": f"missing_groups:{','.join(missing)}"}

    try:
        multiplier = _validated_multiplier(thresholds)
        a_score = float(groups["A"]["artifact_quality_score"])
        d_score = float(groups["D"]["artifact_quality_score"])
    except (KeyError, TypeError, ValueError) as exc:
        return {"verdict": "FAIL", "reason": f"invalid_inputs:{exc}"}

    pass_ok = d_score >= a_score * multiplier
    verdict = "PASS" if pass_ok else "FAIL"
    return {"verdict": verdict, "A": groups["A"], "D": groups["D"]}
