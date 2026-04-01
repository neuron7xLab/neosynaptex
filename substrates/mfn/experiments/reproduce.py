#!/usr/bin/env python3
"""Canonical reproduction script — anyone runs this, gets identical numbers.

Usage:
    uv run python experiments/reproduce.py
    # or
    python experiments/reproduce.py

Expected output: experiments/expected_output.json (committed, versioned)
Actual output:   experiments/actual_output.json (generated)

If actual != expected → something changed. Investigate before merging.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

import mycelium_fractal_net as mfn


def main() -> int:
    print("=" * 60)
    print("MFN CANONICAL REPRODUCTION")
    print("=" * 60)
    t_start = time.perf_counter()

    # ── 1. Simulation (deterministic) ────────────────────────────
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
    field_hash = hashlib.sha256(seq.field.tobytes()).hexdigest()[:16]

    # ── 2. Core diagnosis ────────────────────────────────────────
    report = mfn.diagnose(seq, mode="fast", skip_intervention=True)

    # ── 3. Unified engine ────────────────────────────────────────
    from mycelium_fractal_net.core.unified_engine import UnifiedEngine

    full = UnifiedEngine().analyze(seq)

    # ── 4. Math frontier ─────────────────────────────────────────
    from mycelium_fractal_net.analytics.math_frontier import run_math_frontier

    math = run_math_frontier(seq, run_rmt=True)

    elapsed = (time.perf_counter() - t_start) * 1000

    # ── Build result ─────────────────────────────────────────────
    actual = {
        "simulation": {
            "grid_size": 32,
            "steps": 60,
            "seed": 42,
            "field_hash": field_hash,
            "field_mean": round(float(np.mean(seq.field)), 8),
            "field_std": round(float(np.std(seq.field)), 8),
        },
        "diagnosis": {
            "severity": report.severity,
            "anomaly_label": report.anomaly.label,
            "anomaly_score": round(float(report.anomaly.score), 4),
            "ews_score": round(report.warning.ews_score, 4),
            "causal_decision": report.causal.decision.value,
        },
        "unified": {
            "basin_stability": round(full.basin_stability, 4),
            "delta_alpha": round(full.delta_alpha, 4),
            "hurst_exponent": round(full.hurst_exponent, 4),
            "chi_invariant": round(full.chi_invariant, 4),
            "intervention_level": full.intervention_level,
        },
        "math_frontier": {
            "w2_speed": round(math.w2_trajectory_speed, 4),
            "rmt_r_ratio": round(math.rmt.r_ratio, 4) if math.rmt else None,
            "rmt_structure": math.rmt.structure_type if math.rmt else None,
        },
        "_meta": {
            "compute_time_ms": round(elapsed, 1),
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
    }

    # ── Save actual ──────────────────────────────────────────────
    actual_path = Path(__file__).parent / "actual_output.json"
    actual_path.write_text(json.dumps(actual, indent=2))

    # ── Compare with expected ────────────────────────────────────
    expected_path = Path(__file__).parent / "expected_output.json"
    if not expected_path.exists():
        print(f"\nNo expected output found. Creating: {expected_path}")
        expected_path.write_text(json.dumps(actual, indent=2))
        print(json.dumps(actual, indent=2))
        print(f"\n[OK] Baseline created in {elapsed:.0f}ms")
        return 0

    expected = json.loads(expected_path.read_text())

    # Compare deterministic fields (must be identical)
    mismatches: list[str] = []
    for section in ["simulation", "diagnosis", "unified", "math_frontier"]:
        if section not in expected:
            continue
        for key, exp_val in expected[section].items():
            act_val = actual.get(section, {}).get(key)
            if exp_val is None and act_val is None:
                continue
            if isinstance(exp_val, float) and isinstance(act_val, float):
                if abs(exp_val - act_val) > 0.01:
                    mismatches.append(f"  {section}.{key}: expected={exp_val} actual={act_val}")
            elif exp_val != act_val:
                mismatches.append(f"  {section}.{key}: expected={exp_val} actual={act_val}")

    print(json.dumps(actual, indent=2))

    if mismatches:
        print(f"\n[FAIL] {len(mismatches)} mismatches:")
        for m in mismatches:
            print(m)
        return 1

    print(f"\n[PASS] All values match expected output ({elapsed:.0f}ms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
