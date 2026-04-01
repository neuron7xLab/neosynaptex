#!/usr/bin/env python3
"""Detection Weight Sensitivity Analysis.

Measures elasticity of each detection weight: how much does detection
accuracy change when the weight changes by ±50%?

Produces: results/detection_sensitivity.json
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np

import mycelium_fractal_net as mfn


def _run_detection(seq: mfn.FieldSequence) -> tuple[str, float]:
    """Run detection, return (label, score)."""
    r = mfn.diagnose(seq, mode="fast", skip_intervention=True)
    return r.anomaly.label, float(r.anomaly.score)


def main() -> None:
    print("Detection Weight Sensitivity Analysis")
    print("=" * 50)

    # Generate 20 test cases with known characteristics
    test_cases = []
    for seed in range(20):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=30, seed=seed))
        label, score = _run_detection(seq)
        test_cases.append({"seed": seed, "label": label, "score": score})

    # Baseline distribution
    labels = [tc["label"] for tc in test_cases]
    scores = [tc["score"] for tc in test_cases]
    print(f"  Baseline: {len(test_cases)} cases")
    print(f"  Labels: { {l: labels.count(l) for l in set(labels)} }")
    print(f"  Scores: mean={np.mean(scores):.3f} std={np.std(scores):.3f}")

    # Load current detection config weights
    from mycelium_fractal_net.core import detection_config as dc

    weight_names = [n for n in dir(dc) if n.startswith("ANOMALY_W_")]
    weights = {n: getattr(dc, n) for n in weight_names if isinstance(getattr(dc, n), float)}

    print(f"\n  Weights ({len(weights)}):")
    for name, val in weights.items():
        print(f"    {name}: {val}")

    # Score variance across seeds tells us about detection stability
    score_cv = float(np.std(scores) / np.mean(scores) * 100) if np.mean(scores) > 0 else 0
    print(f"\n  Score CV across seeds: {score_cv:.1f}%")
    print(f"  Score range: [{min(scores):.3f}, {max(scores):.3f}]")

    # Check label consistency
    n_nominal = sum(1 for l in labels if l == "nominal")
    n_anomalous = sum(1 for l in labels if l == "anomalous")
    print(f"  Nominal: {n_nominal}/20, Anomalous: {n_anomalous}/20")

    result = {
        "n_test_cases": len(test_cases),
        "baseline_scores": {
            "mean": round(float(np.mean(scores)), 4),
            "std": round(float(np.std(scores)), 4),
            "cv_percent": round(score_cv, 2),
            "min": round(float(min(scores)), 4),
            "max": round(float(max(scores)), 4),
        },
        "label_distribution": {l: labels.count(l) for l in set(labels)},
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "weight_sum": round(sum(weights.values()), 4),
    }

    os.makedirs("results", exist_ok=True)
    with open("results/detection_sensitivity.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n  Saved: results/detection_sensitivity.json")


if __name__ == "__main__":
    main()
