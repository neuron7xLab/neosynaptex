"""Apply the admissibility rule and emit the six-field verdict block.

The admissibility rule (A1–A4 at primary σ=0.1) is mechanical: walk
the (estimator, N) sub-grid in increasing N, find the smallest N at
which all four conditions hold for every γ_true, declare that as
``N_min``. If no such N exists, the estimator FAILS.

Once each estimator has a per-estimator (PASS/FAIL, N_min) state, the
top-level verdict is fixed:

* canonical_theil_sen passes → CANONICAL_ESTIMATOR=accepted, no
  replacement, FINAL_VERDICT=ADMISSIBLE_AT_N_MIN_<int>.
* canonical fails, at least one alternative passes → reject canonical,
  promote best-by-RMSE alternative, FINAL_VERDICT=ADMISSIBLE_AT_N_MIN_<int>.
* canonical fails, no alternative passes → BLOCKED.

The verdict block is emitted verbatim — every field is present, every
string is exact-spelled. The block is what null-screen consumers will
gate on.
"""

from __future__ import annotations

from typing import Any

from tools.phase_3.admissibility.trial import PRIMARY_SIGMA, _fmt_float

__all__ = [
    "VERDICT_BLOCK_TEMPLATE",
    "build_verdict",
    "format_verdict_block",
]


#: Frozen template; the six fields appear verbatim. Field values are
#: substituted by ``format_verdict_block``.
VERDICT_BLOCK_TEMPLATE: str = (
    "ESTIMATOR_ADMISSIBILITY:\n"
    "  {ESTIMATOR_ADMISSIBILITY}\n"
    "\n"
    "MINIMUM_TRAJECTORY_LENGTH:\n"
    "  {MINIMUM_TRAJECTORY_LENGTH}\n"
    "\n"
    "CANONICAL_ESTIMATOR:\n"
    "  {CANONICAL_ESTIMATOR}\n"
    "\n"
    "REPLACEMENT_ESTIMATOR:\n"
    "  {REPLACEMENT_ESTIMATOR}\n"
    "\n"
    "HYPOTHESIS_TEST_STATUS:\n"
    "  {HYPOTHESIS_TEST_STATUS}\n"
    "\n"
    "FINAL_VERDICT:\n"
    "  {FINAL_VERDICT}\n"
)

# Per-rule thresholds. Mirror the protocol §"ADMISSIBILITY RULE" exactly.
_A1_BIAS_BOUND: float = 0.05
_A2_COVERAGE_FLOOR: float = 0.90
_A3_WINDOW_DELTA_BOUND: float = 0.05
_A4_FPR_BOUND: float = 0.05


def _parse_scalar(x: Any) -> float | None:
    """Coerce a metric scalar (number or "nan" sentinel) to float-or-None."""
    if isinstance(x, (int, float)):
        if x != x:  # NaN guard
            return None
        return float(x)
    if isinstance(x, str):
        if x == "nan":
            return None
        try:
            return float(x)
        except ValueError:
            return None
    return None


def _passes_at_n(
    estimator: str,
    n_key: str,
    cells: dict[str, Any],
    gamma_grid: list[float],
    sigma_key: str,
) -> dict[str, bool]:
    """Check A1–A4 at a single (estimator, N) for the primary σ.

    A1 / A2 / A3 must hold for *every* γ_true. A4 is one-shot per
    (estimator, N, σ) — we use any γ_true cell to read its value
    (the FPR is identical across γ_true for the same (N, σ); the
    trial fills every cell with the same FPR by construction).
    """
    a1_pass = True  # |bias| ≤ 0.05 for every γ_true
    a2_pass = True  # CI coverage ≥ 0.90 for every γ_true
    a3_pass = True  # window_delta_max ≤ 0.05 for every γ_true
    a4_pass = True  # FPR ≤ 0.05

    sample_fpr_seen = False
    for g in gamma_grid:
        g_key = _fmt_float(g)
        cell = cells[estimator][g_key][n_key][sigma_key]
        bias = _parse_scalar(cell["bias"])
        coverage = _parse_scalar(cell["ci95_coverage"])
        wdmax = _parse_scalar(cell["window_delta_max"])
        fpr = _parse_scalar(cell["false_positive_rate_on_null"])

        if bias is None or abs(bias) > _A1_BIAS_BOUND:
            a1_pass = False
        if coverage is None or coverage < _A2_COVERAGE_FLOOR:
            a2_pass = False
        if wdmax is None or wdmax > _A3_WINDOW_DELTA_BOUND:
            a3_pass = False
        if not sample_fpr_seen:
            if fpr is None or fpr > _A4_FPR_BOUND:
                a4_pass = False
            sample_fpr_seen = True

    return {"A1": a1_pass, "A2": a2_pass, "A3": a3_pass, "A4": a4_pass}


def _per_estimator_summary(
    results: dict[str, Any],
    sigma_for_admissibility: float = PRIMARY_SIGMA,
) -> dict[str, dict[str, Any]]:
    """For every estimator: (N_min, status, failed_axes_at_largest_N).

    Walks N_grid in increasing order and returns the smallest N where
    A1+A2+A3+A4 jointly hold. Also reports which axis(es) fail at the
    largest N — useful for the operator to know *why* an estimator
    failed without re-reading the JSON.
    """
    config = results["config"]
    cells = results["cells"]
    sigma_key = _fmt_float(sigma_for_admissibility)
    n_grid: list[int] = list(config["n_grid"])
    gamma_grid: list[float] = list(config["gamma_grid"])

    summary: dict[str, dict[str, Any]] = {}
    for est in config["estimator_names"]:
        n_min: int | None = None
        last_axes: dict[str, bool] = {}
        for n in sorted(n_grid):
            n_key = str(int(n))
            axes = _passes_at_n(est, n_key, cells, gamma_grid, sigma_key)
            last_axes = axes
            if all(axes.values()):
                n_min = int(n)
                break
        # Compute average RMSE at primary σ across γ_grid at N_min
        # (used by the replacement-estimator tiebreaker). When N_min is
        # None we still compute it at the largest N to surface in the
        # diagnostic summary.
        n_for_rmse = int(n_min) if n_min is not None else int(max(n_grid))
        rmse_vals: list[float] = []
        for g in gamma_grid:
            g_key = _fmt_float(g)
            rmse = _parse_scalar(cells[est][g_key][str(n_for_rmse)][sigma_key]["rmse"])
            if rmse is not None:
                rmse_vals.append(rmse)
        avg_rmse = sum(rmse_vals) / len(rmse_vals) if rmse_vals else float("inf")

        summary[est] = {
            "n_min": n_min,
            "status": "PASSED" if n_min is not None else "FAILED",
            "failed_axes_at_largest_N": [k for k, v in last_axes.items() if not v],
            "avg_rmse_at_n_min": avg_rmse,
            "n_used_for_rmse": n_for_rmse,
        }
    return summary


def build_verdict(results: dict[str, Any]) -> dict[str, Any]:
    """Apply the admissibility rule and return the six-field verdict.

    The output dict has exactly the six contractual fields plus a
    ``"per_estimator"`` block carrying diagnostic context (used by
    JSON consumers but NOT part of the human-readable verdict block).
    """
    summary = _per_estimator_summary(results, sigma_for_admissibility=PRIMARY_SIGMA)
    canonical = summary["canonical_theil_sen"]

    if canonical["status"] == "PASSED":
        canonical_status = "accepted"
        replacement = "NONE"
        n_min_int = int(canonical["n_min"])
        admissibility = "PASSED"
        hypothesis_status = f"READY (at N >= {n_min_int})"
        final_verdict = f"ADMISSIBLE_AT_N_MIN_{n_min_int}"
        n_min_field: int | str = n_min_int
    else:
        canonical_status = "rejected"
        # Find replacement: PASSED estimator with lowest avg_rmse_at_n_min.
        candidates = {
            name: meta
            for name, meta in summary.items()
            if name != "canonical_theil_sen" and meta["status"] == "PASSED"
        }
        if candidates:
            best_name = min(candidates, key=lambda k: candidates[k]["avg_rmse_at_n_min"])
            best = candidates[best_name]
            n_min_int = int(best["n_min"])
            replacement = best_name
            admissibility = "PASSED"
            hypothesis_status = f"READY (at N >= {n_min_int})"
            final_verdict = f"ADMISSIBLE_AT_N_MIN_{n_min_int}"
            n_min_field = n_min_int
        else:
            replacement = "NONE"
            admissibility = "FAILED"
            hypothesis_status = "BLOCKED"
            final_verdict = "BLOCKED_BY_MEASUREMENT_OPERATOR"
            n_min_field = "INF"

    return {
        "ESTIMATOR_ADMISSIBILITY": admissibility,
        "MINIMUM_TRAJECTORY_LENGTH": n_min_field,
        "CANONICAL_ESTIMATOR": canonical_status,
        "REPLACEMENT_ESTIMATOR": replacement,
        "HYPOTHESIS_TEST_STATUS": hypothesis_status,
        "FINAL_VERDICT": final_verdict,
        "per_estimator": summary,
    }


def format_verdict_block(verdict: dict[str, Any]) -> str:
    """Render the six-field human-readable block from a verdict dict."""
    return VERDICT_BLOCK_TEMPLATE.format(
        ESTIMATOR_ADMISSIBILITY=verdict["ESTIMATOR_ADMISSIBILITY"],
        MINIMUM_TRAJECTORY_LENGTH=verdict["MINIMUM_TRAJECTORY_LENGTH"],
        CANONICAL_ESTIMATOR=verdict["CANONICAL_ESTIMATOR"],
        REPLACEMENT_ESTIMATOR=verdict["REPLACEMENT_ESTIMATOR"],
        HYPOTHESIS_TEST_STATUS=verdict["HYPOTHESIS_TEST_STATUS"],
        FINAL_VERDICT=verdict["FINAL_VERDICT"],
    )
