"""CLI — Branch A panel-level contrast: healthy (NSR) vs CHF on n=116.

Reads the 116 per-subject baseline JSONs produced by
``scripts.run_hrv_baseline_panel`` and emits a Welch t / Cohen d table
across the classical HRV panel. Healthy = {nsr2db, nsrdb}; pathology =
{chf2db, chfdb}. No MFDFA, no γ — those live in
``scripts.run_mfdfa_full_cohort`` / ``scripts.run_branch_a_blind_validation``.

Usage
-----
  python -m scripts.branch_a_panel_contrast

Outputs
-------
  results/hrv_baseline/branch_a_panel_contrast.json

Claim discipline
----------------
Panel-level contrast only. Does NOT license a clinical marker; does NOT
license Branch A promotion (which requires MFDFA + blind validation per
``manuscript/hrv_bounded_preprint_skeleton.md`` §3.5). This is the
within-substrate, panel-scale separation that the preprint's §4.2
reserves.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.hrv.contrast import contrast_panel  # noqa: E402 — sys.path shim above

HEALTHY = frozenset({"nsr2db", "nsrdb"})
PATHOLOGY = frozenset({"chf2db", "chfdb"})
METRICS = (
    "dfa_alpha1",
    "dfa_alpha2",
    "sample_entropy",
    "sdnn_ms",
    "rmssd_ms",
    "lf_hf_ratio",
    "poincare_sd1_ms",
    "poincare_sd2_ms",
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in-dir", type=Path, default=Path("results/hrv_baseline"))
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    out_path = args.out or (args.in_dir / "branch_a_panel_contrast.json")
    subjects = [json.loads(p.read_text()) for p in sorted(args.in_dir.glob("*__*_baseline.json"))]

    groups: dict[str, dict[str, list[float]]] = {
        "healthy": {m: [] for m in METRICS},
        "pathology": {m: [] for m in METRICS},
    }
    for s in subjects:
        label = (
            "healthy"
            if s["cohort"] in HEALTHY
            else "pathology"
            if s["cohort"] in PATHOLOGY
            else None
        )
        if label is None:
            continue
        for m in METRICS:
            v = s["panel"].get(m)
            if v is not None and math.isfinite(v):
                groups[label][m].append(v)

    panel = contrast_panel(groups["healthy"], groups["pathology"])

    n_healthy = len({s["record"] for s in subjects if s["cohort"] in HEALTHY})
    n_path = len({s["record"] for s in subjects if s["cohort"] in PATHOLOGY})

    report = {
        "schema_version": 1,
        "labels": {
            "healthy": {"cohorts": sorted(HEALTHY), "n_subjects": n_healthy},
            "pathology": {"cohorts": sorted(PATHOLOGY), "n_subjects": n_path},
        },
        "test": "welch_t_two_sided_unpaired",
        "effect_size": "cohen_d_pooled_sd",
        "metrics": {m: _legacy_shape(r.as_json()) for m, r in panel.items()},
        "interpretation_boundary": (
            "Panel-level within-substrate contrast. Classical HRV "
            "features only — no MFDFA, no γ. Does NOT license a "
            "clinical diagnostic claim. Promotion of Branch A to a "
            "per-subject marker requires the MFDFA (h(q=2), Δh) "
            "blind-validation protocol in manuscript/"
            "hrv_bounded_preprint_skeleton.md §3.5."
        ),
    }

    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Branch A panel contrast — healthy n={n_healthy} vs pathology n={n_path}")
    print(f"{'metric':<18} {'healthy':>20} {'pathology':>20} {'t':>8} {'d':>8}")
    for m, r in panel.items():
        print(
            f"{m:<18} {r.mean_a:>10.3f}±{r.std_a:<8.3f} {r.mean_b:>10.3f}±{r.std_b:<8.3f} "
            f"{r.welch_t:>+8.2f} {r.cohen_d:>+8.2f}"
        )
    print(f"→ {out_path}")
    return 0


def _legacy_shape(contrast_json: dict[str, float | int]) -> dict[str, float | int]:
    """Keep the v0.1 JSON keys stable across the refactor (downstream scripts/tables)."""

    return {
        "healthy_mean": contrast_json["mean_a"],
        "healthy_std": contrast_json["std_a"],
        "pathology_mean": contrast_json["mean_b"],
        "pathology_std": contrast_json["std_b"],
        "welch_t": contrast_json["welch_t"],
        "welch_df": contrast_json["welch_df"],
        "cohen_d": contrast_json["cohen_d"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
