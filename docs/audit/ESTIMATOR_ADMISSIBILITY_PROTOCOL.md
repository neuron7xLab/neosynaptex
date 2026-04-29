# Estimator Admissibility Protocol — Phase 3 P0

**Status:** frozen — content changes require a protocol-version bump.
**Authoritative implementation:** `tools/phase_3/admissibility/`.
**Authoritative test battery:** `tests/test_estimator_admissibility.py`.

## 1. Purpose

The Phase 3 null-screen runner emits verdicts of the form
`SIGNAL_SEPARATES_FROM_NULL` only when an estimated γ̂ on a substrate
trajectory differs significantly from γ̂ on a surrogate. Every such
verdict is a function of the γ estimator. If the estimator is itself
unstable — i.e. its window-to-window variation exceeds the effect size
the verdict is supposed to detect — every downstream p-value, every
ledger update, every substrate claim is structurally invalid. The
ruler is broken; it cannot ground a measurement.

This protocol defines a metrological trial that gates whether the
canonical estimator (`tools/phase_3/estimator.py::estimate_gamma`) is
admissible as a ruler. If it is not admissible, the trial selects the
best alternative from a closed set of four; if no alternative passes,
the trial emits `BLOCKED_BY_MEASUREMENT_OPERATOR` and Phase 3 stays
blocked until a replacement estimator is admitted.

## 2. Why upstream of the null-screen

The null-screen runner asks: *given an estimator, does it tell signal
from noise?* The admissibility trial asks the prior question: *is the
estimator itself meaningful at this trajectory length?* Failing to ask
the prior question is the central failure mode the protocol guards
against — running a hypothesis test with an operator whose
window-sweep dispersion (Δγ_max) exceeds the effect size by 100×. The
trial is therefore a P0 gate.

## 3. Synthetic-data model

Power-law:
```
K_i = a · C_i^(-γ_true) · exp(σ · ε_i),    ε_i ~ N(0, 1) IID
```
with `C_i` log-uniform on `[1, 1e5]`, `a = 1.0`, and `σ ∈ {0, 0.05, 0.1,
0.2}`. The primary report is at `σ = 0.1`. A separate "null" mode
(`γ_true = 0`, K independent of C: `K = a · exp(σ · ε)`) supports the
false-positive-rate metric.

## 4. Estimators under trial

1. **canonical_theil_sen** — current canonical: γ = −Theil–Sen slope of
   `log K` vs `log C`, CI from scipy's exact pairwise distribution.
2. **subwindow_bagged_theil_sen** — median over Theil–Sen fits on
   sliding windows of width N/2 stride 1; CI from quantiles of the bag.
3. **quantile_pivoted_slope** — γ = −Q50 of all pairwise slopes; CI
   from Q025/Q975. Equivalent to Theil–Sen on point estimate but with
   a percentile CI rather than the Wilcoxon-rank CI.
4. **bootstrap_median_slope** — B=1000 bootstrap resamples, fit
   Theil–Sen on each, return median γ̂; CI from bootstrap quantiles.
5. **odr_log_log** — orthogonal distance regression on `(log C, log K)`
   with equal x/y errors, γ = −slope, CI from `β̂ ± 1.96 · σ̂_β`.

## 5. Per-cell metrics (8 total)

A "cell" is one `(estimator, γ_true, N, σ)` tuple. For each cell we
draw `M` replicates and compute:

1. **bias** — `mean(γ̂) − γ_true`.
2. **variance** — `var(γ̂)` (ddof=1).
3. **rmse** — `sqrt(mean((γ̂ − γ_true)²))`.
4. **ci95_coverage** — fraction of replicates whose 95 % CI contains
   `γ_true`.
5. **window_delta_max** — per replicate, `max − min` of γ̂ across 4
   sliding windows of width N/2 stride N/8; we take the maximum across
   the first `n_replicates_for_window_metrics` replicates.
6. **leave_one_window_out_drift** — per replicate, `max_i |γ̂_full −
   γ̂_drop_window_i|` for disjoint windows of width N/4; max over the
   capped replicate subset.
7. **bootstrap_slope_dispersion** — per replicate, `std` of B=200
   bootstrap γ̂'s; mean over the capped replicate subset.
8. **false_positive_rate_on_null** — at `γ_true = 0` (null mode),
   fraction of replicates whose 95 % CI excludes 0. Computed once per
   `(estimator, N, σ)` and replicated into every γ_true cell of that
   group for downstream convenience.

## 6. Admissibility rule

For some `N_min ∈ {64, 128, 256, 512, 1024}`, on `σ = 0.1`:

* **A1** `|bias| ≤ 0.05` for every γ_true and every `N ≥ N_min`.
* **A2** `ci95_coverage ≥ 0.90` for every γ_true and every `N ≥ N_min`.
* **A3** `window_delta_max ≤ 0.05` for every γ_true and every `N ≥ N_min`.
* **A4** `false_positive_rate_on_null ≤ α = 0.05` for every `N ≥ N_min`.

`N_min` := smallest N satisfying A1+A2+A3+A4 jointly. If none satisfies,
`N_min = INF` and the estimator FAILS.

## 7. Verdict block (six fields, exact spelling)

```
ESTIMATOR_ADMISSIBILITY:
  <PASSED|FAILED>

MINIMUM_TRAJECTORY_LENGTH:
  <N_min int, or INF>

CANONICAL_ESTIMATOR:
  <accepted|rejected>

REPLACEMENT_ESTIMATOR:
  <name from the four alternatives, or NONE>

HYPOTHESIS_TEST_STATUS:
  <READY|BLOCKED>

FINAL_VERDICT:
  <BLOCKED_BY_MEASUREMENT_OPERATOR | ADMISSIBLE_AT_N_MIN_<int> | EMERGENCY_DOWNGRADE>
```

Branches:

* canonical passes → `accepted`, `REPLACEMENT=NONE`,
  `HYPOTHESIS_TEST_STATUS=READY`,
  `FINAL_VERDICT=ADMISSIBLE_AT_N_MIN_<int>`.
* canonical fails, ≥1 alternative passes → `rejected`, replacement is
  the alternative with the lowest average RMSE at `σ=0.1` at its own
  `N_min`. `READY (at N ≥ N_min)`.
* canonical fails, no alternative passes → `rejected`,
  `REPLACEMENT=NONE`, `HYPOTHESIS_TEST_STATUS=BLOCKED`,
  `FINAL_VERDICT=BLOCKED_BY_MEASUREMENT_OPERATOR`.

## 7a. Smoke vs canonical scope

The CLI has two run modes, controlled by the `--smoke` flag.

* **Canonical** (default; main / merge_group): full grid. M=1000,
  N ∈ {20, 64, 128, 256, 512, 1024}, σ ∈ {0, 0.05, 0.1, 0.2}, all 5
  estimators. Bootstrap B=1000 (per spec). Each estimator runs in its
  own CI matrix leg with a 240-min timeout.
* **Smoke** (`--smoke`; PR-time): reduced grid. M=100, N ∈ {20, 64,
  128, 256}, σ ∈ {0, 0.05, 0.1, 0.2}, all 5 estimators. Bootstrap
  B=100. Each estimator runs in its own matrix leg with a 30-min
  timeout. Smoke trades resolution for throughput; the canonical run
  on main is the authoritative answer.

The smoke caps are an explicit, documented divergence from the per-
spec values. The smoke result_hash and the canonical result_hash will
differ because the full hashable payload includes the bootstrap-B
value; this is by design — the trial is parametric in B and the hash
must reflect the parameter set the verdict was computed under.

## 8. Reproducibility & hash contract

The output JSON's `result_hash` is the sha256 of the canonicalised
payload (sorted keys, no spaces, no NaN/Inf, UTF-8). Wall-clock
timestamps and runtime measurements are stamped *after* hashing so two
identical-config runs produce a byte-identical hash. Enforced by the
test `test_cli_smoke_reproducible_hash`.

## 9. Forbidden conclusions

This protocol explicitly does NOT support:

* "γ ≈ 1 supported by Phase 3."
* "Phase 3 is ready to publish."
* "Substrate X passes the null-screen."
* Any softening words: *probably*, *borderline*, *marginal*, etc.

The trial answers exactly one question: is the ruler usable, and at
what minimum trajectory length? Whatever the data say is what the
verdict block reports.
