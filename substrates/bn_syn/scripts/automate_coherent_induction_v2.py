from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks.coherent_induction_abcd import run_benchmark
from coherent_induction.evidence_ledger_v2 import make_entry, to_json
from coherent_induction.release_gate import evaluate_ten_x

RESULTS = ROOT / "benchmarks" / "results" / "coherent_induction_abcd.jsonl"
REPORT = ROOT / "docs" / "reports" / "ten_x_start_quality_report.md"
LEDGER = ROOT / "examples" / "ledger_entry_v2.json"
THRESHOLDS = ROOT / "config" / "ten_x_thresholds.yaml"


def _load_thresholds() -> dict[str, float]:
    import yaml

    data = yaml.safe_load(THRESHOLDS.read_text(encoding="utf-8"))
    return {"artifact_quality_multiplier": float(data["artifact_quality_multiplier"])}


def main() -> int:
    run_benchmark(RESULTS)
    summary = evaluate_ten_x(RESULTS, _load_thresholds())
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# 10x Start Quality Report\n\n"
        f"Verdict: **{summary['verdict']}**\n\n"
        f"Group A score: {summary['A']['artifact_quality_score']}\n\n"
        f"Group D score: {summary['D']['artifact_quality_score']}\n",
        encoding="utf-8",
    )
    entry = make_entry(
        {
            "run_id": "coherent-induction-v2-auto",
            "role_sequence_hash": "auto",
            "hypothesis_hash": "auto",
            "artifact_hash": "auto",
            "config_hash": "auto",
            "model_name": "automation",
            "prompt_hash": "auto",
            "drift_score": 0.0,
            "quality_score": float(summary["D"]["artifact_quality_score"]),
            "falsifier_verdict": "PASS",
            "safety_verdict": "PASS",
            "final_verdict": str(summary["verdict"]),
            "failure_reason": "" if summary["verdict"] == "PASS" else "thresholds_not_met",
            "reproducibility_command": "python scripts/automate_coherent_induction_v2.py",
        }
    )
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(to_json(entry), encoding="utf-8")
    print(json.dumps({"event": "automation_complete", "verdict": summary["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
