"""CLI — compute the 11-metric HRV baseline panel on every cohort subject.

Usage
-----
  python -m scripts.run_hrv_baseline_panel                # all 116 subjects
  python -m scripts.run_hrv_baseline_panel --cohorts nsr2db chfdb
  python -m scripts.run_hrv_baseline_panel --source live  # re-fetch via wfdb

Outputs
-------
  results/hrv_baseline/{cohort}__{record}_baseline.json   (116 files)
  results/hrv_baseline/panel_summary.json                 (cohort roll-up)

Inputs
------
By default the script reads cached RR arrays from
``data/raw/{cohort}/{record}.rr.npy`` (gitignored; regenerate via
``python -m scripts.build_physionet_cohort_manifests``). ``--source
live`` fetches via wfdb each time.

Claim discipline
----------------
This CLI measures HRV features only. It does **not** compute γ, does
**not** run nulls, and does **not** compare NSR vs CHF. Those belong
to Tasks 5 / 6 / 8 / 9 downstream.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np

from tools.data.physionet_cohort import COHORTS, fetch_record
from tools.hrv.baseline_panel import compute_baseline_panel


def _load_rr(cohort: str, record: str, source: str, cache_dir: Path) -> np.ndarray | None:
    if source == "cache":
        path = cache_dir / cohort / f"{record}.rr.npy"
        if not path.exists():
            return None
        return np.load(path, allow_pickle=False)
    # live
    rec = fetch_record(COHORTS[cohort], record, cache_dir=cache_dir / cohort)
    if rec.status != "ok":
        return None
    return np.load(cache_dir / cohort / f"{record}.rr.npy", allow_pickle=False)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cohorts", nargs="*", choices=sorted(COHORTS), default=list(COHORTS))
    ap.add_argument("--source", choices=["cache", "live"], default="cache")
    ap.add_argument("--cache-dir", type=Path, default=Path("data/raw"))
    ap.add_argument("--out-dir", type=Path, default=Path("results/hrv_baseline"))
    args = ap.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    cohort_rollup: dict[str, list[dict]] = {c: [] for c in args.cohorts}
    total = sum(COHORTS[c].expected_n_subjects for c in args.cohorts)
    done = 0
    rc = 0

    for cohort in args.cohorts:
        spec = COHORTS[cohort]
        _log(f"cohort {cohort}: {spec.expected_n_subjects} subjects")
        for record in spec.expected_records:
            done += 1
            rr = _load_rr(cohort, record, args.source, args.cache_dir)
            if rr is None:
                _log(f"  [{done:3d}/{total}] {cohort}:{record} SKIP (no cache + no live)")
                rc = 1
                continue
            panel = compute_baseline_panel(rr)
            entry = {
                "cohort": cohort,
                "record": record,
                "panel": dataclasses.asdict(panel),
            }
            out = args.out_dir / f"{cohort}__{record}_baseline.json"
            out.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            cohort_rollup[cohort].append(entry["panel"])
            _log(
                f"  [{done:3d}/{total}] {cohort}:{record}  "
                f"α₁={panel.dfa_alpha1:.2f}  α₂={panel.dfa_alpha2:.2f}  "
                f"SDNN={panel.sdnn_ms:.0f}ms  LF/HF={panel.lf_hf_ratio:.2f}  "
                f"SampEn={panel.sample_entropy:.2f}"
            )

    # Summary: per-cohort means (audit trail, not a claim)
    summary: dict[str, dict] = {
        "schema_version": 1,
        "cohorts_ran": args.cohorts,
        "n_subjects_total": total,
        "per_cohort": {},
    }
    for cohort, rows in cohort_rollup.items():
        if not rows:
            continue
        keys = [k for k in rows[0] if isinstance(rows[0][k], int | float)]
        agg = {}
        for k in keys:
            vals = np.array([r[k] for r in rows], dtype=np.float64)
            finite = vals[np.isfinite(vals)]
            agg[k] = {
                "n_finite": int(finite.size),
                "mean": float(finite.mean()) if finite.size else float("nan"),
                "std": float(finite.std(ddof=1)) if finite.size > 1 else float("nan"),
                "min": float(finite.min()) if finite.size else float("nan"),
                "max": float(finite.max()) if finite.size else float("nan"),
            }
        summary["per_cohort"][cohort] = {"n_subjects": len(rows), "metrics": agg}
    summary_path = args.out_dir / "panel_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _log(f"summary → {summary_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
