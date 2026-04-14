"""CLI — Branch A panel-level contrast: healthy (NSR) vs CHF on n=116.

Reads the 116 per-subject baseline JSONs produced by
``scripts.run_hrv_baseline_panel`` and emits a single Welch t / Cohen d
table across the classical HRV panel. Healthy = {nsr2db, nsrdb};
pathology = {chf2db, chfdb}. No MFDFA, no γ — those live in the
multifractal pipeline.

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
placeholder reserves.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, stdev

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


def _welch(a: list[float], b: list[float]) -> dict[str, float]:
    na, nb = len(a), len(b)
    ma, mb = mean(a), mean(b)
    va, vb = stdev(a) ** 2, stdev(b) ** 2
    se = math.sqrt(va / na + vb / nb)
    t = (ma - mb) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    sp = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    d = (ma - mb) / sp
    return {
        "healthy_mean": round(ma, 4),
        "healthy_std": round(math.sqrt(va), 4),
        "pathology_mean": round(mb, 4),
        "pathology_std": round(math.sqrt(vb), 4),
        "welch_t": round(t, 3),
        "welch_df": round(df, 1),
        "cohen_d": round(d, 3),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in-dir", type=Path, default=Path("results/hrv_baseline"))
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    out_path = args.out or (args.in_dir / "branch_a_panel_contrast.json")
    subjects = [json.loads(p.read_text()) for p in sorted(args.in_dir.glob("*__*_baseline.json"))]

    buckets: dict[str, dict[str, list[float]]] = {
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
                buckets[label][m].append(v)

    contrast = {m: _welch(buckets["healthy"][m], buckets["pathology"][m]) for m in METRICS}
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
        "metrics": contrast,
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
    for m, row in contrast.items():
        hm, hs = row["healthy_mean"], row["healthy_std"]
        pm, ps = row["pathology_mean"], row["pathology_std"]
        print(
            f"{m:<18} {hm:>10.3f}±{hs:<8.3f} {pm:>10.3f}±{ps:<8.3f} "
            f"{row['welch_t']:>+8.2f} {row['cohen_d']:>+8.2f}"
        )
    print(f"→ {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
