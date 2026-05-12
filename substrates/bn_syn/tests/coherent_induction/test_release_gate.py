import json
from pathlib import Path

from coherent_induction.release_gate import evaluate_ten_x


def test_release_gate_uses_benchmark_evidence(tmp_path: Path) -> None:
    p = tmp_path / "r.jsonl"
    p.write_text("\n".join([
        json.dumps({"group": "A", "artifact_quality_score": 30.0}),
        json.dumps({"group": "D", "artifact_quality_score": 70.0}),
    ]))
    out = evaluate_ten_x(p, {"artifact_quality_multiplier": 2.0})
    assert out["verdict"] == "PASS"


def test_release_gate_fails_closed_when_group_missing(tmp_path: Path) -> None:
    p = tmp_path / "r.jsonl"
    p.write_text(json.dumps({"group": "A", "artifact_quality_score": 30.0}))
    out = evaluate_ten_x(p, {"artifact_quality_multiplier": 2.0})
    assert out["verdict"] == "FAIL"
    assert out["reason"] == "missing_groups:D"
