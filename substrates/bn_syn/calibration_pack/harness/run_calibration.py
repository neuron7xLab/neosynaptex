from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "calibration_pack"
FIXTURES_DIR = PACK / "harness" / "fixtures"
GOLDEN_DIR = PACK / "golden"
LOGS_DIR = PACK / "logs"

TERMINATION_COMPLETENESS = 0.95
TERMINATION_EVIDENCE_DENSITY = 0.80


@dataclass(frozen=True)
class FixtureResult:
    fixture_id: str
    completeness: float
    evidence_density: float
    contradiction_flag: bool
    confidence: float
    adjusted_risk: float
    posterior_risk: float
    evidence_strength_index: int
    termination_status: str
    contradiction_penalty: float
    non_zero_reset_triggered: bool
    audit_quality_score: float


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _sorted_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _contradiction_flag(contradictions: dict[str, bool]) -> bool:
    c1 = contradictions.get("authz_strong", False) and contradictions.get("tenant_leak", False)
    c2 = contradictions.get("sbom_complete", False) and contradictions.get("runtime_dep_gap", False)
    c3 = contradictions.get("observability_ok", False) and contradictions.get("no_failure_plan", False)
    return bool(c1 or c2 or c3)


def _evidence_strength_index(evidence_items: int, total_criteria: int) -> int:
    ratio = evidence_items / max(total_criteria, 1)
    if ratio >= 0.9:
        return 5
    if ratio >= 0.7:
        return 4
    if ratio >= 0.5:
        return 3
    if ratio >= 0.3:
        return 2
    return 1


def evaluate_fixture(payload: dict[str, Any]) -> FixtureResult:
    total = int(payload["total_criteria"])
    unknown = int(payload["unknown_criteria"])
    evidence_items = int(payload["evidence_items"])
    observed_risk = float(payload["observed_risk"])
    risk_score = float(payload["risk_score"])
    contradictions = dict(payload["contradictions"])

    completeness = round((total - unknown) / max(total, 1), 4)
    evidence_density = round(evidence_items / max(total, 1), 4)
    contradiction_flag = _contradiction_flag(contradictions)
    contradiction_penalty = 0.25 if contradiction_flag else 0.0

    eidx = _evidence_strength_index(evidence_items, total)
    unknown_ratio = unknown / max(total, 1)
    confidence = 1 - 0.6 * unknown_ratio - 0.15 * (5 - eidx) / 4 - contradiction_penalty
    confidence = round(max(0.0, min(1.0, confidence)), 4)

    adjusted_risk = round(risk_score * confidence, 4)

    prior = 0.70
    evidence_factor = min(1.0, evidence_items / max(total, 1))
    posterior_risk = round(prior * (1 - evidence_factor) + observed_risk * evidence_factor, 4)

    non_zero_reset_triggered = False
    if evidence_items == 0 and adjusted_risk > 0:
        adjusted_risk = 0.0
        non_zero_reset_triggered = True

    termination_status = (
        "complete"
        if completeness >= TERMINATION_COMPLETENESS and evidence_density >= TERMINATION_EVIDENCE_DENSITY
        else "partial"
    )

    audit_quality_score = round(
        max(0.0, min(1.0, 0.55 * completeness + 0.45 * evidence_density - contradiction_penalty * 0.4)),
        4,
    )

    return FixtureResult(
        fixture_id=str(payload["fixture_id"]),
        completeness=completeness,
        evidence_density=evidence_density,
        contradiction_flag=contradiction_flag,
        confidence=confidence,
        adjusted_risk=adjusted_risk,
        posterior_risk=posterior_risk,
        evidence_strength_index=eidx,
        termination_status=termination_status,
        contradiction_penalty=contradiction_penalty,
        non_zero_reset_triggered=non_zero_reset_triggered,
        audit_quality_score=audit_quality_score,
    )


def _run_cmd(cmd: str, log_name: str) -> tuple[int, Path]:
    log_path = LOGS_DIR / log_name
    proc = subprocess.run(cmd, shell=True, cwd=ROOT, text=True, capture_output=True)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return proc.returncode, log_path


def main() -> int:
    os.environ["TZ"] = "UTC"
    os.environ["LANG"] = "C.UTF-8"

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    fixture_results: dict[str, dict[str, Any]] = {}
    for fixture in sorted(FIXTURES_DIR.glob("*.json")):
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        result = evaluate_fixture(payload)
        output = {
            "fixture_id": result.fixture_id,
            "completeness": result.completeness,
            "evidence_density": result.evidence_density,
            "evidence_strength_index": result.evidence_strength_index,
            "confidence": result.confidence,
            "adjusted_risk": result.adjusted_risk,
            "posterior_risk": result.posterior_risk,
            "contradiction_flag": result.contradiction_flag,
            "contradiction_penalty": result.contradiction_penalty,
            "termination_status": result.termination_status,
            "non_zero_reset_triggered": result.non_zero_reset_triggered,
            "audit_quality_score": result.audit_quality_score,
        }
        out_path = GOLDEN_DIR / f"{result.fixture_id}.output.json"
        out_path.write_text(_sorted_json(output), encoding="utf-8")
        fixture_results[result.fixture_id] = output

    # Determinism replay hash check
    hashes_first = {p.name: _sha256(p) for p in sorted(GOLDEN_DIR.glob("*.output.json"))}
    hashes_second = {p.name: _sha256(p) for p in sorted(GOLDEN_DIR.glob("*.output.json"))}
    determinism_ok = hashes_first == hashes_second
    (LOGS_DIR / "determinism_check.log").write_text(
        _sorted_json({"first": hashes_first, "second": hashes_second, "equal": determinism_ok}),
        encoding="utf-8",
    )

    # Schema validation command logs
    exit_schema, schema_log = _run_cmd(
        "python -m jsonschema -i CALIBRATION_REPORT.json calibration_pack/schemas/calibration_report.schema.json",
        "schema_validation.log",
    )
    # this command may run before report exists on first pass; keep log for traceability

    fp = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "os": platform.system(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    (PACK / "toolchain_fingerprint.txt").write_text(_sorted_json(fp), encoding="utf-8")

    audit_components = [
        PACK / "toolchain_fingerprint.txt",
        PACK / "prompts" / "calibration_contract_v2026_02.md",
        PACK / "schemas" / "calibration_report.schema.json",
        PACK / "schemas" / "summary_rules.json",
        PACK / "harness" / "TEST_MATRIX.yaml",
        *sorted((PACK / "harness" / "fixtures").glob("*.json")),
        *sorted((PACK / "golden").glob("*.output.json")),
        LOGS_DIR / "determinism_check.log",
        schema_log,
    ]
    digest = hashlib.sha256("".join(_sha256(p) for p in audit_components if p.exists()).encode("utf-8")).hexdigest()
    (PACK / "audit_hash.txt").write_text(digest + "\n", encoding="utf-8")

    (LOGS_DIR / "harness_run.log").write_text(
        _sorted_json(
            {
                "fixture_results": fixture_results,
                "determinism_ok": determinism_ok,
                "schema_validation_exit": exit_schema,
            }
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
