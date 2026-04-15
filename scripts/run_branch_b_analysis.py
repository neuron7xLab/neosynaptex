"""CLI — Branch B §5.3 cross-subject γ analysis.

Reads per-subject γ-fits produced by ``scripts.run_gamma_full_cohort``
and emits the Branch B full-cohort verdict:

- Per-cohort and per-group (healthy / pathology) γ distribution
  (mean, SD, min, max, 95 % CI on the mean via percentile bootstrap).
- Two-sided one-sample t-test of H₀: E[γ] = 1 on the healthy group
  (the universal-γ framing under examination).
- Welch / Mann-Whitney U contrast between healthy and pathology γ
  distributions, with Cohen d and Cliff's δ (each with 95 % CI).
- Verdict: the universal-γ hypothesis at the cardiac substrate is
  either ``falsified``, ``inconclusive``, or ``consistent`` by the
  decision rule documented in :func:`_verdict`.

Usage
-----
  python -m scripts.run_branch_b_analysis

Inputs
------
  results/hrv_gamma/{cohort}__{record}_gamma.json

Outputs
-------
  results/hrv_gamma/branch_b_analysis.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.hrv.contrast import contrast  # noqa: E402
from tools.stats.effect_size import bootstrap_ci  # noqa: E402
from tools.stats.tests import one_sample_t_test  # noqa: E402

HEALTHY_COHORTS = frozenset({"nsr2db", "nsrdb"})
PATHOLOGY_COHORTS = frozenset({"chf2db", "chfdb"})


def _round_p(p: float) -> float:
    if p != p:
        return p
    if p < 1e-4:
        return float(f"{p:.2e}")
    return round(p, 4)


def _group_stats(values: list[float], *, seed: int, n_boot: int) -> dict[str, object]:
    if not values:
        return {"n": 0}
    n = len(values)
    m = sum(values) / n
    s2 = sum((v - m) ** 2 for v in values) / (n - 1) if n >= 2 else 0.0

    # Percentile bootstrap on the mean.
    def _mean_of(a, _b):  # bootstrap_ci signature is (fn, a, b) — use b as padding
        return sum(a) / len(a)

    try:
        _, ci_lo, ci_hi = bootstrap_ci(_mean_of, values, values, n_boot=n_boot, seed=seed)
    except Exception:  # noqa: BLE001
        ci_lo = ci_hi = float("nan")

    return {
        "n": n,
        "mean": round(m, 4),
        "std": round(s2**0.5, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean_ci95_bootstrap": [round(ci_lo, 4), round(ci_hi, 4)],
    }


def _verdict(one_sample_p: float, group_mean_ci: list[float]) -> str:
    """Decision rule for Branch B at the cardiac substrate.

    * ``falsified`` — one-sample t rejects H₀: γ = 1 at α = 0.01 AND
      the healthy-cohort 95 % bootstrap CI on mean γ excludes 1.0.
    * ``consistent`` — the 95 % CI on mean γ contains 1.0 AND the
      one-sample t fails to reject at α = 0.05.
    * ``inconclusive`` — otherwise.
    """

    lo, hi = group_mean_ci
    ci_excludes_one = lo > 1.0 or hi < 1.0
    ci_contains_one = lo <= 1.0 <= hi
    if one_sample_p < 0.01 and ci_excludes_one:
        return "falsified"
    if one_sample_p >= 0.05 and ci_contains_one:
        return "consistent"
    return "inconclusive"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in-dir", type=Path, default=Path("results/hrv_gamma"))
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--bootstrap-n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    out_path = args.out or (args.in_dir / "branch_b_analysis.json")
    subjects = [json.loads(p.read_text()) for p in sorted(args.in_dir.glob("*__*_gamma.json"))]

    per_cohort: dict[str, list[float]] = {}
    healthy: list[float] = []
    pathology: list[float] = []
    for s in subjects:
        if s.get("status") != "ok":
            continue
        g = s["gamma"]
        if g is None:
            continue
        per_cohort.setdefault(s["cohort"], []).append(float(g))
        if s["cohort"] in HEALTHY_COHORTS:
            healthy.append(float(g))
        elif s["cohort"] in PATHOLOGY_COHORTS:
            pathology.append(float(g))

    report: dict[str, object] = {
        "schema_version": 1,
        "per_cohort": {
            c: _group_stats(vs, seed=args.seed + i, n_boot=args.bootstrap_n)
            for i, (c, vs) in enumerate(sorted(per_cohort.items()))
        },
        "groups": {
            "healthy": _group_stats(healthy, seed=args.seed, n_boot=args.bootstrap_n),
            "pathology": _group_stats(pathology, seed=args.seed + 1, n_boot=args.bootstrap_n),
        },
    }

    # H₀: E[γ] = 1 on healthy group.
    if len(healthy) >= 2:
        ts = one_sample_t_test(healthy, mu_0=1.0)
        report["h0_gamma_equals_one"] = {
            "group": "healthy",
            "mu_0": 1.0,
            **ts.as_json(),
        }
        verdict = _verdict(
            ts.p_value,
            report["groups"]["healthy"]["mean_ci95_bootstrap"],
        )
    else:
        verdict = "insufficient_data"

    # Healthy vs pathology γ contrast (two-sample).
    if len(healthy) >= 2 and len(pathology) >= 2:
        c = contrast(healthy, pathology)
        report["healthy_vs_pathology_contrast"] = {
            "welch_t": round(c.welch_t, 3),
            "welch_df": round(c.welch_df, 1),
            "welch_p": _round_p(c.welch_p),
            "mwu_p": _round_p(c.mwu_p),
            "cohen_d": round(c.cohen_d, 3),
            "cohen_d_ci95": [round(c.cohen_d_ci_low, 3), round(c.cohen_d_ci_high, 3)],
            "cliffs_delta": round(c.cliffs_delta, 3),
            "cliffs_delta_ci95": [
                round(c.cliffs_delta_ci_low, 3),
                round(c.cliffs_delta_ci_high, 3),
            ],
        }

    report["verdict"] = verdict
    report["interpretation_boundary"] = (
        "Branch B §5.3: cross-subject γ distribution at the cardiac "
        "substrate. A ``falsified`` verdict rejects the universal-γ ≈ 1 "
        "framing at the cardiac substrate; a ``consistent`` verdict "
        "does NOT license the universal framing — it only means the "
        "cardiac substrate does not contradict it at n=116. The "
        "verdict is bounded to this substrate and the VLF band "
        "[0.003, 0.04] Hz; it does not transfer to other substrates "
        "or bands."
    )

    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Branch B — cross-subject γ on n={len(healthy) + len(pathology)} subjects")
    print(f"  healthy  n={len(healthy):>3}  " + json.dumps(report["groups"]["healthy"]))
    print(f"  pathology n={len(pathology):>3}  " + json.dumps(report["groups"]["pathology"]))
    if "h0_gamma_equals_one" in report:
        h0 = report["h0_gamma_equals_one"]
        print(
            f"  H₀: E[γ]=1 on healthy → t={h0['statistic']:.3f}, df={h0['df']}, p={h0['p_value']}"
        )
    print(f"  verdict: {verdict}")
    print(f"→ {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
