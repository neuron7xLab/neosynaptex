"""Sensitivity analysis for detection thresholds.

For each of the top-20 decision thresholds, perturbs by ±5%, ±10%, ±20%
and measures label flip rate across validation scenarios.

Usage:
    python scripts/sensitivity_sweep.py

Output:
    docs/reports/SENSITIVITY_ANALYSIS.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.detect import detect_anomaly

# Scenarios to test
SCENARIOS = [
    mfn.SimulationSpec(grid_size=24, steps=12, seed=42),
    mfn.SimulationSpec(grid_size=24, steps=12, seed=7),
    mfn.SimulationSpec(grid_size=24, steps=12, seed=123),
    mfn.SimulationSpec(grid_size=24, steps=12, seed=42, alpha=0.22),
    mfn.SimulationSpec(grid_size=24, steps=12, seed=42, alpha=0.08),
    mfn.SimulationSpec(grid_size=32, steps=16, seed=42),
]

# Top thresholds to test (from detection_config)
from mycelium_fractal_net.core import detection_config as dc

THRESHOLDS = {
    "DYNAMIC_ANOMALY_BASELINE": ("dc", "DYNAMIC_ANOMALY_BASELINE"),
    "STABLE_CEILING": ("dc", "STABLE_CEILING"),
    "THRESHOLD_FLOOR": ("dc", "THRESHOLD_FLOOR"),
    "THRESHOLD_CEILING": ("dc", "THRESHOLD_CEILING"),
    "WATCH_THRESHOLD_FLOOR": ("dc", "WATCH_THRESHOLD_FLOOR"),
    "WATCH_THRESHOLD_GAP": ("dc", "WATCH_THRESHOLD_GAP"),
    "PATHOLOGICAL_NOISE_THRESHOLD": ("dc", "PATHOLOGICAL_NOISE_THRESHOLD"),
    "REORGANIZED_COMPLEXITY_THRESHOLD": ("dc", "REORGANIZED_COMPLEXITY_THRESHOLD"),
    "REORGANIZED_PLASTICITY_FLOOR": ("dc", "REORGANIZED_PLASTICITY_FLOOR"),
    "STRUCTURE_FLOOR": ("dc", "STRUCTURE_FLOOR"),
}

PERTURBATIONS = [0.05, 0.10, 0.20]


def _baseline_labels() -> list[tuple[str, str]]:
    """Get baseline labels for all scenarios."""
    labels = []
    for spec in SCENARIOS:
        seq = mfn.simulate(spec)
        det = detect_anomaly(seq)
        labels.append((det.label, det.regime.label))
    return labels


def _perturbed_labels(attr_name: str, original: float, factor: float) -> list[tuple[str, str]]:
    """Get labels after perturbing a threshold."""
    setattr(dc, attr_name, original * (1.0 + factor))
    try:
        labels = []
        for spec in SCENARIOS:
            seq = mfn.simulate(spec)
            det = detect_anomaly(seq)
            labels.append((det.label, det.regime.label))
        return labels
    finally:
        setattr(dc, attr_name, original)


def main() -> None:
    print("Running sensitivity sweep...")
    baseline = _baseline_labels()
    n_scenarios = len(SCENARIOS)

    results: list[dict] = []

    for name, (_, attr) in THRESHOLDS.items():
        original = getattr(dc, attr)
        row = {"threshold": name, "value": original, "perturbations": {}}

        for pct in PERTURBATIONS:
            flips_up = 0
            flips_down = 0

            labels_up = _perturbed_labels(attr, original, pct)
            labels_down = _perturbed_labels(attr, original, -pct)

            for i in range(n_scenarios):
                if labels_up[i] != baseline[i]:
                    flips_up += 1
                if labels_down[i] != baseline[i]:
                    flips_down += 1

            flip_rate = max(flips_up, flips_down) / n_scenarios
            row["perturbations"][f"±{int(pct * 100)}%"] = {
                "flips_up": flips_up,
                "flips_down": flips_down,
                "flip_rate": round(flip_rate, 2),
                "fragile": flip_rate > 0.10,
            }

        results.append(row)

    # Generate report
    report_dir = Path(__file__).resolve().parents[1] / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "SENSITIVITY_ANALYSIS.md"

    lines = [
        "# Sensitivity Analysis — Detection Thresholds\n",
        f"Scenarios tested: {n_scenarios}\n",
        f"Thresholds analyzed: {len(THRESHOLDS)}\n",
        "",
        "| Threshold | Value | ±5% flips | ±10% flips | ±20% flips | Fragile? |",
        "|-----------|-------|-----------|------------|------------|----------|",
    ]

    fragile_count = 0
    for r in results:
        p5 = r["perturbations"]["±5%"]
        p10 = r["perturbations"]["±10%"]
        p20 = r["perturbations"]["±20%"]
        fragile = "YES" if any(p["fragile"] for p in r["perturbations"].values()) else "no"
        if fragile == "YES":
            fragile_count += 1
        lines.append(
            f"| {r['threshold']} | {r['value']:.3f} | "
            f"{p5['flip_rate']:.0%} | {p10['flip_rate']:.0%} | {p20['flip_rate']:.0%} | "
            f"{fragile} |"
        )

    lines.extend(
        [
            "",
            f"**Fragile thresholds (>10% flip at ±5%): {fragile_count}**",
            "",
            "Fragile thresholds should be reviewed for robustness.",
            "See `configs/detection_thresholds_v1.json` for current values.",
        ]
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report: {report_path}")

    # Also save JSON
    json_path = report_dir / "sensitivity_analysis.json"
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Data: {json_path}")


if __name__ == "__main__":
    main()
