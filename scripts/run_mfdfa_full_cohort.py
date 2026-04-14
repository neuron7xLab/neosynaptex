"""CLI — MFDFA over the full n=116 PhysioNet cardiac cohort.

Reads cached RR arrays from ``data/raw/{cohort}/{record}.rr.npy`` and
writes per-subject MFDFA records plus a cohort roll-up. Offline only.
See :mod:`tools.hrv.mfdfa_cohort` for the algorithmic contract.

Usage
-----
  python -m scripts.run_mfdfa_full_cohort                       # all 116
  python -m scripts.run_mfdfa_full_cohort --cohorts nsr2db chfdb
  python -m scripts.run_mfdfa_full_cohort --rr-truncate 10000

Outputs
-------
  results/hrv_mfdfa/{cohort}__{record}_mfdfa.json
  results/hrv_mfdfa/cohort_summary.json

Claim discipline
----------------
Produces ``(h(q=2), Δh)`` per subject. Does **not** fit a classifier,
does **not** declare Branch A promoted. Promotion requires the blind-
validation CLI (``scripts.run_branch_a_blind_validation``).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.data.physionet_cohort import COHORTS  # noqa: E402
from tools.hrv.mfdfa_cohort import run_cohort_mfdfa  # noqa: E402


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cohorts", nargs="*", choices=sorted(COHORTS), default=list(COHORTS))
    ap.add_argument("--cache-dir", type=Path, default=Path("data/raw"))
    ap.add_argument("--out-dir", type=Path, default=Path("results/hrv_mfdfa"))
    ap.add_argument("--rr-truncate", type=int, default=20000)
    ap.add_argument("--fit-order", type=int, default=1)
    args = ap.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pairs = [(c, rec) for c in args.cohorts for rec in COHORTS[c].expected_records]
    _log(f"MFDFA: {len(args.cohorts)} cohorts × {len(pairs)} subjects total")
    t0 = time.time()

    subjects = run_cohort_mfdfa(
        pairs,
        cache_dir=args.cache_dir,
        rr_truncate=args.rr_truncate,
        fit_order=args.fit_order,
    )

    for s in subjects:
        out = args.out_dir / f"{s.cohort}__{s.record}_mfdfa.json"
        out.write_text(json.dumps(s.as_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if s.status == "ok":
            _log(f"  {s.cohort}:{s.record}  h(q=2)={s.h_at_q2:.3f}  Δh={s.delta_h:.3f}")
        else:
            _log(f"  {s.cohort}:{s.record}  {s.status}")

    ok = [s for s in subjects if s.status == "ok"]
    summary: dict[str, object] = {
        "schema_version": 1,
        "rr_truncate": args.rr_truncate,
        "fit_order": args.fit_order,
        "q_values": [round(-3.0 + 0.5 * i, 1) for i in range(13)],
        "n_subjects_attempted": len(subjects),
        "n_subjects_ok": len(ok),
        "n_subjects_failed": len(subjects) - len(ok),
        "per_cohort": {},
        "runtime_seconds": round(time.time() - t0, 1),
    }
    for cohort in args.cohorts:
        rows = [s for s in ok if s.cohort == cohort]
        if not rows:
            continue
        h = [s.h_at_q2 for s in rows if s.h_at_q2 is not None]
        d = [s.delta_h for s in rows if s.delta_h is not None]
        summary["per_cohort"][cohort] = {
            "n_ok": len(rows),
            "h_at_q2_mean": round(sum(h) / len(h), 4) if h else None,
            "h_at_q2_min": round(min(h), 4) if h else None,
            "h_at_q2_max": round(max(h), 4) if h else None,
            "delta_h_mean": round(sum(d) / len(d), 4) if d else None,
            "delta_h_min": round(min(d), 4) if d else None,
            "delta_h_max": round(max(d), 4) if d else None,
        }
    (args.out_dir / "cohort_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _log(f"summary → {args.out_dir / 'cohort_summary.json'}  ({len(ok)}/{len(subjects)} ok)")
    return 0 if len(ok) == len(subjects) else 1


if __name__ == "__main__":
    raise SystemExit(main())
