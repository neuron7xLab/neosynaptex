"""CLI — build PhysioNet cardiac cohort manifests.

Usage
-----
  python -m scripts.build_physionet_cohort_manifests                 # all 4 cohorts
  python -m scripts.build_physionet_cohort_manifests nsr2db chfdb    # subset
  python -m scripts.build_physionet_cohort_manifests --no-cache      # manifest only

Outputs
-------
  data/manifests/{cohort}_manifest.json           (committed)
  data/raw/{cohort}/{record}.rr.npy               (gitignored, optional)

Runs a live wfdb fetch against PhysioNet. Network-dependent. Prints a
per-record OK/FAIL line to stderr so slow/flaky fetches are visible.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from tools.data.physionet_cohort import COHORTS, build_manifest, write_manifest


def _log(n: int, total: int, record: str, status: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {n:3d}/{total:3d} {record:12s} {status}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build PhysioNet cardiac cohort manifests via wfdb.")
    ap.add_argument(
        "cohorts",
        nargs="*",
        choices=sorted(COHORTS),
        help="Cohort names to build (default: all 4).",
    )
    ap.add_argument(
        "--manifests-dir",
        type=Path,
        default=Path("data/manifests"),
        help="Output dir for manifest JSONs.",
    )
    ap.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/raw"),
        help="Parent dir for per-cohort RR .npy caches.",
    )
    ap.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip writing RR .npy caches (manifest only).",
    )
    args = ap.parse_args(argv)

    cohort_names = args.cohorts or sorted(COHORTS)
    rc = 0
    for name in cohort_names:
        spec = COHORTS[name]
        print(
            f"[cohort] {name}: expecting {spec.expected_n_subjects} subjects "
            f"from {spec.source_url}",
            file=sys.stderr,
        )
        cache = None if args.no_cache else args.cache_dir / name
        manifest = build_manifest(spec, cache_dir=cache, on_progress=_log)
        out = args.manifests_dir / f"{name}_manifest.json"
        write_manifest(manifest, out)
        ok = manifest["actual_n_subjects"]
        exp = manifest["expected_n_subjects"]
        mark = "OK" if ok == exp else "INCOMPLETE"
        print(f"[cohort] {name}: {ok}/{exp} {mark} → {out}", file=sys.stderr)
        if ok != exp:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
