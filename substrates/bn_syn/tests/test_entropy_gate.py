from __future__ import annotations

from pathlib import Path
import json

from tools.entropy_gate.compute_metrics import compute_metrics, flatten


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"NEEDS_EVIDENCE: missing required file: {path.as_posix()}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_entropy_gate_no_regressions() -> None:
    repo_root = _repo_root()
    policy = _load_json(repo_root / "entropy" / "policy.json")
    baseline = _load_json(repo_root / "entropy" / "baseline.json")

    current = compute_metrics(repo_root)

    comparators: dict[str, str] = policy.get("comparators", {})
    assert comparators, "NEEDS_EVIDENCE: policy.json comparators missing/empty"

    baseline_flat = flatten(baseline)
    current_flat = flatten(current)

    failures: list[str] = []
    for key, comparator in sorted(comparators.items()):
        if key not in baseline_flat:
            failures.append(f"{key}: NEEDS_EVIDENCE baseline missing key")
            continue
        if key not in current_flat:
            failures.append(f"{key}: NEEDS_EVIDENCE current missing key")
            continue

        baseline_value = baseline_flat[key]
        current_value = current_flat[key]

        if comparator == "lte":
            if not (current_value <= baseline_value):
                failures.append(
                    f"{key}: regression (current={current_value} > baseline={baseline_value})"
                )
        elif comparator == "gte":
            if not (current_value >= baseline_value):
                failures.append(
                    f"{key}: regression (current={current_value} < baseline={baseline_value})"
                )
        elif comparator == "eq":
            if not (current_value == baseline_value):
                failures.append(
                    f"{key}: changed (current={current_value} != baseline={baseline_value})"
                )
        else:
            failures.append(f"{key}: NEEDS_EVIDENCE unknown comparator '{comparator}'")

    assert not failures, "ENTROPY_GATE_BLOCKED:\n" + "\n".join(failures)
