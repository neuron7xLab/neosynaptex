"""Baseline parity."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.types.field import SimulationSpec

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "evidence" / "wave_8"
CONTRACTS = ROOT / "docs" / "contracts"
SHOWCASE_MANIFEST = ROOT / "artifacts" / "showcase" / "showcase_manifest.json"
ETALON_JSON = CONTRACTS / "showcase_run.etalon.json"
ETALON_SHA = CONTRACTS / "showcase_run.etalon.sha256"


def _stable_payload() -> dict[str, object]:
    spec = SimulationSpec(grid_size=32, steps=24, seed=42, alpha=0.16, spike_probability=0.22)
    seq = mfn.simulate_history(spec)
    descriptor = mfn.extract(seq)
    detection = mfn.detect(seq)
    forecast = mfn.forecast(seq, horizon=6)
    comparison = mfn.compare(seq, seq)
    return {
        "contract_version": "showcase-etalon-v1",
        "spec": spec.to_dict(),
        "descriptor_version": descriptor.version,
        "anomaly_label": detection.label,
        "regime_label": (detection.regime.label if detection.regime is not None else None),
        "forecast_method": forecast.method,
        "comparison_label": comparison.label,
        "comparison_topology_label": comparison.topology_label,
        "comparison_reorganization_label": comparison.reorganization_label,
        "forecast_benchmark_metrics": {k: float(v) for k, v in forecast.benchmark_metrics.items()},
    }


def _digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _ensure_showcase_run() -> None:
    if SHOWCASE_MANIFEST.exists():
        return
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "showcase_run.py")],
        cwd=ROOT,
        check=True,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    _ensure_showcase_run()
    payload = _stable_payload()
    digest = _digest(payload)
    if not ETALON_JSON.exists():
        ETALON_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if not ETALON_SHA.exists():
        ETALON_SHA.write_text(digest + "\n", encoding="utf-8")

    expected = json.loads(ETALON_JSON.read_text(encoding="utf-8"))
    expected_digest = ETALON_SHA.read_text(encoding="utf-8").strip()

    spec_a = SimulationSpec(grid_size=16, steps=8, seed=42)
    spec_b = SimulationSpec.from_dict({**spec_a.to_dict(), "neuromodulation": None})
    left = mfn.simulate_history(spec_a)
    right = mfn.simulate_history(spec_b)
    baseline_parity = bool(
        np.array_equal(left.field, right.field)
        and np.array_equal(left.history, right.history)
        and left.to_dict().keys() == right.to_dict().keys()
    )

    report = {
        "ok": baseline_parity and payload == expected and digest == expected_digest,
        "baseline_parity_neuromodulation_none": baseline_parity,
        "showcase_etalon_match": payload == expected,
        "showcase_hash_match": digest == expected_digest,
        "expected_sha256": expected_digest,
        "actual_sha256": digest,
        "etalon_path": str(ETALON_JSON.relative_to(ROOT)),
        "hash_path": str(ETALON_SHA.relative_to(ROOT)),
        "showcase_manifest": str(SHOWCASE_MANIFEST.relative_to(ROOT)),
    }
    (OUT / "baseline_parity_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
