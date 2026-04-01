from __future__ import annotations

import json
from pathlib import Path

REQUIRED_ARTIFACTS = [
    Path("docs/ENTROPY_LEDGER.md"),
    Path("entropy/metrics.json"),
    Path("entropy/commands.log"),
    Path("entropy/acceptance_map.yaml"),
    Path("evidence/entropy/baseline.json"),
    Path("evidence/entropy/final.json"),
]


def _load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def run_guard(repo_root: Path) -> list[str]:
    errors: list[str] = []

    for artifact in REQUIRED_ARTIFACTS:
        if not (repo_root / artifact).exists():
            errors.append(f"missing required artifact: {artifact}")

    metrics_path = repo_root / "entropy/metrics.json"
    acceptance_path = repo_root / "entropy/acceptance_map.yaml"
    if not metrics_path.exists() or not acceptance_path.exists():
        return errors

    metrics = _load_json(metrics_path)
    acceptance = _load_json(acceptance_path)

    baseline = metrics.get("baseline")
    final = metrics.get("final")
    if not isinstance(baseline, dict) or not isinstance(final, dict):
        errors.append("entropy/metrics.json must include baseline and final objects")
        return errors

    criteria = acceptance.get("criteria")
    if not isinstance(criteria, list):
        errors.append("entropy/acceptance_map.yaml must include criteria list")
        return errors

    for criterion in criteria:
        if not isinstance(criterion, dict):
            errors.append("invalid criterion entry")
            continue
        metric_id = criterion.get("metric")
        threshold = criterion.get("threshold")
        direction = criterion.get("direction")
        if not isinstance(metric_id, str) or threshold is None or not isinstance(direction, str):
            errors.append("criterion missing metric/threshold/direction")
            continue

        final_value = final.get(metric_id)
        if not isinstance(final_value, (int, float)):
            errors.append(f"final metric missing numeric value: {metric_id}")
            continue

        numeric_threshold = float(threshold)
        if direction == "gte" and final_value < numeric_threshold:
            errors.append(f"{metric_id}={final_value} < {numeric_threshold}")
        elif direction == "lte" and final_value > numeric_threshold:
            errors.append(f"{metric_id}={final_value} > {numeric_threshold}")
        elif direction not in {"gte", "lte"}:
            errors.append(f"unsupported direction for {metric_id}: {direction}")

    return errors


def main() -> int:
    errors = run_guard(Path("."))
    if errors:
        for error in errors:
            print(f"[entropy-guard] {error}")
        return 1
    print("[entropy-guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
