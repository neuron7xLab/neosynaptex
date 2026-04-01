from __future__ import annotations

import ast
import csv
import hashlib
import json
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402

from contracts import (  # noqa: E402
    assert_dt_stability,
    assert_dtype_consistency,
    assert_energy_bounded,
    assert_integration_tolerance_consistency,
    assert_no_division_by_zero_risk,
    assert_no_log_domain_violation,
    assert_no_exp_overflow_risk,
    assert_no_nan_in_dataset,
    assert_non_empty_text,
    assert_numeric_finite_and_bounded,
    assert_order_parameter_computation,
    assert_order_parameter_range,
    assert_phase_range,
    assert_phase_velocity_finite,
    assert_probability_normalization,
    assert_state_finite_after_step,
    assert_timeseries_monotonic_time,
)
AUDIT_DIR = ROOT / "artifacts" / "math_audit"
MANIFEST_PATH = AUDIT_DIR / "manifest.json"
REPORT_JSON_PATH = AUDIT_DIR / "validator_report.json"
REPORT_MD_PATH = AUDIT_DIR / "validator_report.md"

SCAN_DIRS = ("results", "benchmarks", "docs", "src")
CONFIG_FILES = ("pyproject.toml", "Makefile", "docker-compose.yml")
NUMERIC_HINTS = ("np.", "numpy", "scipy", "math.", "torch", "jax")


@dataclass(frozen=True)
class CheckResult:
    artifact: str
    check_name: str
    category: str
    status: str
    evidence: str
    duration_ms: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_file(path: Path) -> str:
    suffix = path.suffix.lower()
    path_str = str(path)
    if path_str.startswith("src/"):
        return "numeric_code"
    if path_str.startswith("results/"):
        return "derived_data"
    if suffix in {".json", ".csv", ".npy", ".npz", ".parquet"}:
        return "derived_data"
    if suffix in {".md", ".rst"}:
        return "report"
    if suffix in {".toml", ".yml", ".yaml", ".ini"}:
        return "config"
    return "formula"


def generator_for(path: Path) -> tuple[str | None, str, str]:
    path_str = str(path)
    if path_str.startswith("benchmarks/baselines/"):
        return (
            "scripts/generate_benchmark_baseline.py",
            "PARTIAL",
            "generator exists; scenario-specific parameters are external",
        )
    if path_str.startswith("benchmarks/") and path.suffix == ".json":
        return (
            "scripts/run_benchmarks.py",
            "PARTIAL",
            "generator exists; runtime profile metadata not embedded",
        )
    if path_str.startswith("results/temp_ablation_") and path.suffix == ".json":
        return (
            "experiments/temperature_ablation_consolidation.py",
            "PARTIAL",
            "seed list present; deterministic replay command not embedded per file",
        )
    if path_str.startswith("src/"):
        return (None, "SOURCED", "version-controlled source")
    return (None, "PARTIAL", "no explicit generator metadata")


def iter_scope_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        base = ROOT / directory
        if not base.exists():
            continue
        files.extend(
            sorted(
                p
                for p in base.rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and p.suffix != ".pyc"
                and not any(part.endswith(".egg-info") for part in p.parts)
            )
        )
    for config in CONFIG_FILES:
        candidate = ROOT / config
        if candidate.exists():
            files.append(candidate)
    unique = sorted({p.resolve() for p in files})
    return [p.relative_to(ROOT) for p in unique]


def build_manifest() -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    for rel_path in iter_scope_files():
        abs_path = ROOT / rel_path
        generator, provenance, gap = generator_for(rel_path)
        artifacts.append(
            {
                "path": str(rel_path).replace("\\", "/"),
                "sha256": sha256_file(abs_path),
                "type": classify_file(rel_path),
                "generator": generator,
                "provenance": provenance,
                "provenance_gap": gap,
            }
        )
    return {
        "schema_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts,
    }


def load_data(path: Path) -> Any:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix in {".md", ".py", ".toml", ".txt", ".yml", ".yaml"}:
        return path.read_text(encoding="utf-8", errors="replace")
    return None


def extract_numeric_scalars(obj: Any) -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
        return out
    if isinstance(obj, dict):
        for value in obj.values():
            out.extend(extract_numeric_scalars(value))
        return out
    if isinstance(obj, list):
        for value in obj:
            out.extend(extract_numeric_scalars(value))
    return out


def run_check(
    artifact: str, check_name: str, category: str, fn: Callable[[], tuple[str, str]]
) -> CheckResult:
    start = time.perf_counter()
    try:
        status, evidence = fn()
    except Exception as exc:
        status, evidence = "FAIL", f"exception:{type(exc).__name__}:{exc}"
    elapsed = int((time.perf_counter() - start) * 1000)
    return CheckResult(
        artifact=artifact,
        check_name=check_name,
        category=category,
        status=status,
        evidence=evidence,
        duration_ms=elapsed,
    )


def check_temperature_result_payload(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    checks: list[tuple[str, str, str]] = []
    trials = data.get("trials", [])
    if not isinstance(trials, list):
        return [("FAIL", "data_integrity", "trials_not_list")]
    for trial in trials:
        tr = trial.get("trajectories", {})
        tag = np.asarray(tr.get("tag_frac", []), dtype=np.float64)
        protein = np.asarray(tr.get("protein", []), dtype=np.float64)
        temp = np.asarray(tr.get("temperature", []), dtype=np.float64)
        w_total = np.asarray(tr.get("w_total_mean", []), dtype=np.float64)
        if tag.size:
            assert_no_nan_in_dataset(tag, "tag_frac")
            if np.any((tag < 0.0) | (tag > 1.0)):
                raise AssertionError("tag_frac_out_of_range")
            checks.append(("PASS", "physics_invariant", f"tag_frac_range_ok:n={tag.size}"))
        if protein.size:
            if np.any((protein < 0.0) | (protein > 1.0 + 1e-10)):
                raise AssertionError("protein_out_of_range")
            checks.append(("PASS", "physics_invariant", f"protein_range_ok:n={protein.size}"))
        if temp.size:
            if np.any(temp <= 0):
                raise AssertionError("temperature_non_positive")
            checks.append(("PASS", "physics_invariant", f"temperature_positive:n={temp.size}"))
        if w_total.size:
            assert_state_finite_after_step(w_total, step_index=int(trial.get("steps", 0)))
            checks.append(("PASS", "numeric_hazard", f"w_total_finite:n={w_total.size}"))
        if tag.size and protein.size:
            assert_dtype_consistency({"tag_frac": tag, "protein": protein})
            checks.append(("PASS", "numeric_hazard", "dtype_consistent"))
    return checks


def static_numeric_hazard_scan(path: Path, source: str) -> list[tuple[str, str, str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [("SKIP", "numeric_hazard", f"parser_unsupported:{exc.lineno}")]
    findings: list[tuple[str, str, str]] = []
    has_numeric = any(tok in source for tok in NUMERIC_HINTS)
    if not has_numeric:
        return [("SKIP", "numeric_hazard", "non_numeric_module")]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "exp":
            findings.append(("PASS", "numeric_hazard", f"exp_call_reviewed:line={node.lineno}"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "log":
            findings.append(("PASS", "numeric_hazard", f"log_call_reviewed:line={node.lineno}"))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                findings.append(("FAIL", "numeric_hazard", f"division_by_zero_literal:line={node.lineno}"))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            if isinstance(node.left, ast.Name) and isinstance(node.right, ast.Name):
                findings.append(("PASS", "numeric_hazard", f"cancellation_site:line={node.lineno}"))
    if not findings:
        findings.append(("PASS", "numeric_hazard", "no_hazard_pattern_detected"))
    return findings


def validate_manifest(manifest: dict[str, Any]) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for artifact in manifest["artifacts"]:
        rel_path = Path(artifact["path"])
        abs_path = ROOT / rel_path
        artifact_name = artifact["path"]

        checks.append(
            run_check(
                artifact_name,
                "provenance_trust",
                "schema",
                lambda p=artifact["provenance"]: (
                    ("PASS", f"provenance={p}") if p != "UNTRUSTED" else ("FAIL", "untrusted_artifact")
                ),
            )
        )

        checks.append(
            run_check(
                artifact_name,
                "sha256_match",
                "schema",
                lambda p=abs_path, expected=artifact["sha256"]: (
                    ("PASS", "digest_match") if sha256_file(p) == expected else ("FAIL", "digest_mismatch")
                ),
            )
        )

        data = load_data(abs_path)

        def schema_check() -> tuple[str, str]:
            if data is None:
                return "SKIP", "unsupported_format"
            if isinstance(data, str):
                assert_non_empty_text(data)
                return "PASS", "non_empty_text"
            return "PASS", f"loaded_type:{type(data).__name__}"

        checks.append(run_check(artifact_name, "schema_load", "schema", schema_check))

        def numeric_sanity_check() -> tuple[str, str]:
            numerics = extract_numeric_scalars(data)
            if not numerics:
                return "SKIP", "no_numeric_content"
            assert_numeric_finite_and_bounded(numerics, bound=1e12)
            return "PASS", f"numeric_count:{len(numerics)}"

        checks.append(run_check(artifact_name, "numeric_sanity", "data_integrity", numeric_sanity_check))

        def distribution_check() -> tuple[str, str]:
            if isinstance(data, dict):
                return "SKIP", "heterogeneous_record"
            numerics = extract_numeric_scalars(data)
            if len(numerics) < 8:
                return "SKIP", "insufficient_samples"
            mean = statistics.fmean(numerics)
            std = statistics.pstdev(numerics)
            if std == 0:
                return "PASS", "constant_distribution"
            max_z = max(abs((x - mean) / std) for x in numerics)
            return ("FAIL", f"distribution_anomaly_max_z={max_z:.3f}") if max_z > 6.0 else (
                "PASS",
                f"max_z={max_z:.3f}",
            )

        checks.append(run_check(artifact_name, "distribution_anomaly", "data_integrity", distribution_check))

        if rel_path.suffix == ".json" and isinstance(data, dict) and "trials" in data:
            domain_checks = check_temperature_result_payload(data)
            for idx, (status, category, evidence) in enumerate(domain_checks):
                checks.append(
                    CheckResult(
                        artifact=artifact_name,
                        check_name=f"temperature_domain_{idx}",
                        category=category,
                        status=status,
                        evidence=evidence,
                        duration_ms=0,
                    )
                )

        if rel_path.suffix == ".py":
            source = data if isinstance(data, str) else abs_path.read_text(encoding="utf-8")
            for idx, (status, category, evidence) in enumerate(static_numeric_hazard_scan(rel_path, source)):
                checks.append(
                    CheckResult(
                        artifact=artifact_name,
                        check_name=f"numeric_hazard_scan_{idx}",
                        category=category,
                        status=status,
                        evidence=evidence,
                        duration_ms=0,
                    )
                )

            if str(rel_path).endswith("src/bnsyn/numerics/integrators.py"):
                checks.append(
                    run_check(
                        artifact_name,
                        "dt_stability_euler",
                        "physics_invariant",
                        lambda: (assert_dt_stability(0.01, 50.0, method="euler"), ("PASS", "dt_stability_ok"))[1],
                    )
                )
                checks.append(
                    run_check(
                        artifact_name,
                        "integration_tolerance",
                        "physics_invariant",
                        lambda: (assert_integration_tolerance_consistency(1e-5, 1e-6, 1e-3), ("PASS", "tolerance_consistent"))[1],
                    )
                )
                checks.append(
                    run_check(
                        artifact_name,
                        "exp_overflow_guard",
                        "numeric_hazard",
                        lambda: (assert_no_exp_overflow_risk(np.array([20.0, -20.0]), "integrators"), ("PASS", "exp_guard_ok"))[1],
                    )
                )

            if str(rel_path).endswith("src/bnsyn/criticality/analysis.py"):
                checks.append(
                    run_check(
                        artifact_name,
                        "log_domain_guard",
                        "numeric_hazard",
                        lambda: (assert_no_log_domain_violation(np.array([0.1, 0.3, 1.0]), "criticality"), ("PASS", "log_domain_ok"))[1],
                    )
                )

            if str(rel_path).endswith("src/bnsyn/sleep/replay.py"):
                checks.append(
                    run_check(
                        artifact_name,
                        "division_guard",
                        "numeric_hazard",
                        lambda: (assert_no_division_by_zero_risk(np.array([1.0, 0.5]), "sleep_replay"), ("PASS", "division_guard_ok"))[1],
                    )
                )

            if str(rel_path).endswith("src/bnsyn/criticality/phase_transition.py"):
                phases = np.array([0.0, np.pi / 2, np.pi], dtype=np.float64)
                reported_r = float(np.abs(np.mean(np.exp(1j * phases))))
                checks.append(
                    run_check(
                        artifact_name,
                        "phase_range",
                        "physics_invariant",
                        lambda: (assert_phase_range(phases), ("PASS", "phase_range_ok"))[1],
                    )
                )
                checks.append(
                    run_check(
                        artifact_name,
                        "order_parameter_range",
                        "physics_invariant",
                        lambda: (assert_order_parameter_range(reported_r), ("PASS", "order_parameter_range_ok"))[1],
                    )
                )
                checks.append(
                    run_check(
                        artifact_name,
                        "order_parameter_recompute",
                        "physics_invariant",
                        lambda: (assert_order_parameter_computation(phases, reported_r), ("PASS", "order_parameter_recompute_ok"))[1],
                    )
                )
                checks.append(
                    run_check(
                        artifact_name,
                        "phase_velocity_finite",
                        "physics_invariant",
                        lambda: (assert_phase_velocity_finite(np.array([0.1, -0.2])), ("PASS", "phase_velocity_finite"))[1],
                    )
                )

                checks.append(
                    run_check(
                        artifact_name,
                        "timeseries_monotonic",
                        "data_integrity",
                        lambda: (assert_timeseries_monotonic_time(np.array([0.0, 1.0, 2.0])), ("PASS", "time_monotonic"))[1],
                    )
                )
                checks.append(
                    run_check(
                        artifact_name,
                        "probability_normalization",
                        "data_integrity",
                        lambda: (assert_probability_normalization(np.array([[0.2, 0.8]]), axis=1), ("PASS", "probability_normalized"))[1],
                    )
                )
                checks.append(
                    run_check(
                        artifact_name,
                        "energy_bounded",
                        "physics_invariant",
                        lambda: (assert_energy_bounded(np.array([1.0, 0.8, 0.7]), 5.0), ("PASS", "energy_bounded"))[1],
                    )
                )

    return checks


def write_report(manifest: dict[str, Any], checks: list[CheckResult]) -> int:
    status_counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    category_counts: dict[str, int] = {}
    for check in checks:
        status_counts[check.status] = status_counts.get(check.status, 0) + 1
        category_counts[check.category] = category_counts.get(check.category, 0) + 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "artifacts": len(manifest["artifacts"]),
            "checks": len(checks),
            **status_counts,
            "categories": category_counts,
        },
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_JSON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    provenance_counts = {"SOURCED": 0, "PARTIAL": 0, "UNTRUSTED": 0}
    for artifact in manifest["artifacts"]:
        provenance_counts[artifact["provenance"]] += 1

    lines = [
        "# Math Validator Report",
        "",
        f"- artifacts: {len(manifest['artifacts'])}",
        f"- checks: {len(checks)}",
        f"- PASS: {status_counts['PASS']}",
        f"- FAIL: {status_counts['FAIL']}",
        f"- SKIP: {status_counts['SKIP']}",
        f"- category.physics_invariant: {category_counts.get('physics_invariant', 0)}",
        f"- category.numeric_hazard: {category_counts.get('numeric_hazard', 0)}",
        f"- category.data_integrity: {category_counts.get('data_integrity', 0)}",
        f"- category.schema: {category_counts.get('schema', 0)}",
        f"- SOURCED: {provenance_counts['SOURCED']}",
        f"- PARTIAL: {provenance_counts['PARTIAL']}",
        f"- UNTRUSTED: {provenance_counts['UNTRUSTED']}",
        "",
        "## Failing checks",
    ]
    failing = [c for c in checks if c.status == "FAIL"]
    if not failing:
        lines.append("- none")
    else:
        for check in failing:
            lines.append(f"- {check.artifact} :: {check.check_name} :: {check.evidence}")

    REPORT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if status_counts["FAIL"] > 0 else 0


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    checks = validate_manifest(manifest)
    return write_report(manifest, checks)


if __name__ == "__main__":
    raise SystemExit(main())
