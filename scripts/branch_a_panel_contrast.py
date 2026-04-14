"""CLI — Branch A panel-level contrast: healthy (NSR) vs CHF on n=116.

Reads the 116 per-subject baseline JSONs produced by
``scripts.run_hrv_baseline_panel`` and emits a contrast table that
now carries, per metric:

- Welch's t with Satterthwaite df and two-sided p-value.
- Mann-Whitney U with its own two-sided p-value (non-parametric check).
- Cohen's d with a 95 % Hedges-Olkin analytical CI.
- Cliff's δ with a 95 % CI (non-parametric effect size).
- Benjamini-Hochberg FDR q-values across the panel for both Welch
  and Mann-Whitney U, so a reader sees at a glance which effects
  survive multiple-testing correction.

Healthy = {nsr2db, nsrdb}; pathology = {chf2db, chfdb}. No MFDFA,
no γ — those live in ``scripts.run_mfdfa_full_cohort`` /
``scripts.run_branch_a_blind_validation``.

Usage
-----
  python -m scripts.branch_a_panel_contrast

Outputs
-------
  results/hrv_baseline/branch_a_panel_contrast.json  (schema v2)

Claim discipline
----------------
Panel-level contrast only. Does NOT license a clinical marker; does NOT
license Branch A promotion (which requires MFDFA + blind validation per
``manuscript/hrv_bounded_preprint_skeleton.md`` §3.5).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.hrv.contrast import panel_with_fdr  # noqa: E402 — sys.path shim

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


def _round_p(p: float) -> float:
    if p != p:
        return p
    if p < 1e-4:
        return float(f"{p:.2e}")
    return round(p, 4)


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

    panel = panel_with_fdr(groups["healthy"], groups["pathology"])

    n_healthy = len({s["record"] for s in subjects if s["cohort"] in HEALTHY})
    n_path = len({s["record"] for s in subjects if s["cohort"] in PATHOLOGY})

    metrics_block: dict[str, dict[str, object]] = {}
    for row in panel:
        r = row.contrast
        metrics_block[row.metric] = {
            "healthy_mean": round(r.mean_a, 4),
            "healthy_std": round(r.std_a, 4),
            "pathology_mean": round(r.mean_b, 4),
            "pathology_std": round(r.std_b, 4),
            "welch_t": round(r.welch_t, 3),
            "welch_df": round(r.welch_df, 1),
            "welch_p": _round_p(r.welch_p),
            "welch_q_bh": _round_p(row.welch_q_bh),
            "mann_whitney_u": round(r.mwu_u, 2),
            "mann_whitney_p": _round_p(r.mwu_p),
            "mann_whitney_q_bh": _round_p(row.mwu_q_bh),
            "cohen_d": round(r.cohen_d, 3),
            "cohen_d_ci95": [round(r.cohen_d_ci_low, 3), round(r.cohen_d_ci_high, 3)],
            "cliffs_delta": round(r.cliffs_delta, 3),
            "cliffs_delta_ci95": [
                round(r.cliffs_delta_ci_low, 3),
                round(r.cliffs_delta_ci_high, 3),
            ],
        }

    report = {
        "schema_version": 2,
        "labels": {
            "healthy": {"cohorts": sorted(HEALTHY), "n_subjects": n_healthy},
            "pathology": {"cohorts": sorted(PATHOLOGY), "n_subjects": n_path},
        },
        "tests": {
            "parametric": "welch_t_two_sided_unpaired",
            "non_parametric": "mann_whitney_u_two_sided",
            "effect_sizes": ["cohen_d_pooled_sd_hedges_olkin_ci", "cliffs_delta_wald_ci"],
            "multiple_testing": "benjamini_hochberg_fdr",
        },
        "metrics": metrics_block,
        "interpretation_boundary": (
            "Panel-level within-substrate contrast with per-metric p "
            "(Welch + Mann-Whitney U), BH-FDR q across the panel, and "
            "95 % CIs on Cohen d and Cliff's δ. Does NOT license a "
            "clinical diagnostic claim. Promotion of Branch A to a "
            "per-subject marker requires the MFDFA (h(q=2), Δh) "
            "blind-validation protocol in manuscript/"
            "hrv_bounded_preprint_skeleton.md §3.5."
        ),
    }

    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Branch A panel contrast — healthy n={n_healthy} vs pathology n={n_path}")
    header = (
        f"{'metric':<18} {'healthy':>18} {'pathology':>18} "
        f"{'d [95% CI]':>20} {'p(Welch)':>10} {'q(BH)':>10}"
    )
    print(header)
    for row in panel:
        r = row.contrast
        d_ci = f"{r.cohen_d:+.2f} [{r.cohen_d_ci_low:+.2f},{r.cohen_d_ci_high:+.2f}]"
        print(
            f"{row.metric:<18} {r.mean_a:>8.2f}±{r.std_a:<8.2f} "
            f"{r.mean_b:>8.2f}±{r.std_b:<8.2f} {d_ci:>20} "
            f"{r.welch_p:>10.1e} {row.welch_q_bh:>10.1e}"
        )
    print(f"→ {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
