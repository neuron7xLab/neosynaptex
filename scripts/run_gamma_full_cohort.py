"""CLI — VLF γ-fit over the full n=116 PhysioNet cardiac cohort.

Per-subject Welch PSD + Theil-Sen slope on the VLF band [0.003, 0.04]
Hz, fed from ``data/raw/{cohort}/{record}.rr.npy``. Produces the
per-subject γ distribution that §5.3 of the preprint skeleton reserves
for Branch B.

Usage
-----
  python -m scripts.run_gamma_full_cohort                       # all 116
  python -m scripts.run_gamma_full_cohort --cohorts nsr2db nsrdb

Outputs
-------
  results/hrv_gamma/{cohort}__{record}_gamma.json
  results/hrv_gamma/cohort_summary.json

Claim discipline
----------------
Produces ``γ, CI95, R², n_freq`` per subject. Does **not** compute
the cross-cohort H₀: γ = 1 test or bootstrap the mean γ; that lives
in ``scripts.run_branch_b_analysis``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.data.physionet_cohort import COHORTS  # noqa: E402
from tools.hrv.gamma_cohort import run_cohort_gamma  # noqa: E402


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cohorts", nargs="*", choices=sorted(COHORTS), default=list(COHORTS))
    ap.add_argument("--cache-dir", type=Path, default=Path("data/raw"))
    ap.add_argument("--out-dir", type=Path, default=Path("results/hrv_gamma"))
    ap.add_argument("--rr-truncate", type=int, default=20000)
    ap.add_argument("--fit-lo-hz", type=float, default=0.003)
    ap.add_argument("--fit-hi-hz", type=float, default=0.04)
    ap.add_argument("--nperseg", type=int, default=1024)
    ap.add_argument("--bootstrap-n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pairs = [(c, rec) for c in args.cohorts for rec in COHORTS[c].expected_records]
    _log(f"γ-fit: {len(args.cohorts)} cohorts × {len(pairs)} subjects")
    t0 = time.time()

    subjects = run_cohort_gamma(
        pairs,
        cache_dir=args.cache_dir,
        rr_truncate=args.rr_truncate,
        fit_lo_hz=args.fit_lo_hz,
        fit_hi_hz=args.fit_hi_hz,
        nperseg=args.nperseg,
        bootstrap_n=args.bootstrap_n,
        seed=args.seed,
    )

    for s in subjects:
        out = args.out_dir / f"{s.cohort}__{s.record}_gamma.json"
        out.write_text(json.dumps(s.as_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if s.status == "ok":
            _log(
                f"  {s.cohort}:{s.record}  γ={s.gamma:+.3f} "
                f"CI=[{s.gamma_ci_low:+.3f},{s.gamma_ci_high:+.3f}]  r²={s.r2:.2f}"
            )
        else:
            _log(f"  {s.cohort}:{s.record}  {s.status}")

    ok = [s for s in subjects if s.status == "ok"]
    summary: dict[str, object] = {
        "schema_version": 1,
        "fit_lo_hz": args.fit_lo_hz,
        "fit_hi_hz": args.fit_hi_hz,
        "nperseg": args.nperseg,
        "rr_truncate": args.rr_truncate,
        "bootstrap_n": args.bootstrap_n,
        "seed": args.seed,
        "n_subjects_attempted": len(subjects),
        "n_subjects_ok": len(ok),
        "per_cohort": {},
        "runtime_seconds": round(time.time() - t0, 1),
    }
    for cohort in args.cohorts:
        rows = [s for s in ok if s.cohort == cohort]
        if not rows:
            continue
        gs = [s.gamma for s in rows]
        summary["per_cohort"][cohort] = {
            "n_ok": len(rows),
            "gamma_mean": round(sum(gs) / len(gs), 4),
            "gamma_min": round(min(gs), 4),
            "gamma_max": round(max(gs), 4),
        }
    (args.out_dir / "cohort_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _log(f"summary → {args.out_dir / 'cohort_summary.json'}  ({len(ok)}/{len(subjects)} ok)")
    return 0 if len(ok) == len(subjects) else 1


if __name__ == "__main__":
    raise SystemExit(main())
