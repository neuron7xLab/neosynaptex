"""Criticality sweep."""

from __future__ import annotations

import json
from pathlib import Path

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.simulate import simulate_scenario
from mycelium_fractal_net.pipelines.reporting import build_analysis_report

OUT = Path("artifacts/showcase/criticality_sweep")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    modes = {
        "baseline": simulate_scenario("synthetic_morphology"),
        "inhibitory_stabilization": simulate_scenario("inhibitory_stabilization"),
        "serotonergic_reorganization": simulate_scenario("regime_transition"),
        "balanced_criticality": simulate_scenario("balanced_criticality"),
        "noise_control": simulate_scenario("sensor_grid_anomaly"),
    }
    summary: dict[str, dict] = {}
    for name, seq in modes.items():
        desc = mfn.extract(seq)
        det = mfn.detect(seq)
        fc = mfn.forecast(seq, horizon=6)
        report = build_analysis_report(seq, OUT / "runs", horizon=6)
        summary[name] = {
            "descriptor_version": desc.version,
            "D_box": float(desc.features.get("D_box", 0.0)),
            "LZC": float(desc.complexity.get("temporal_lzc", 0.0)),
            "modularity": float(desc.connectivity.get("modularity_proxy", 0.0)),
            "connectivity_divergence": float(desc.connectivity.get("connectivity_divergence", 0.0)),
            "clamp_pressure": float(desc.stability.get("collapse_risk_score", 0.0)),
            "forecast_uncertainty": float(fc.uncertainty_envelope.get("ensemble_std_mV", 0.0)),
            "regime_label": det.regime.label if det.regime else "n/a",
            "report_dir": str((OUT / "runs" / report.run_id).resolve()),
        }
    manifest = {"modes": summary}
    (OUT / "criticality_sweep_summary.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
