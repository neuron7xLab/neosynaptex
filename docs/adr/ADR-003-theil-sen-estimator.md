# ADR-003 — Theil-Sen estimator for gamma regression

**Status:** Accepted

---

## Context

The gamma-scaling exponent is estimated from (log topo, log cost) point pairs
via linear regression in log-log space:

```
log(K) = -gamma * log(C) + log(A)
```

The fitting method must be:

1. Robust to outliers — substrate data is noisy and can contain spikes.
2. Non-parametric — we make no distributional assumption about residuals.
3. Consistent with the canonical `core/gamma.py` computation used in the
   published evidence ledger.

---

## Decision

Use **Theil-Sen slope estimator** (`scipy.stats.theilslopes`) for the gamma
regression, implemented in `core/gamma.py::compute_gamma` and mirrored in
the per-domain computation inside `neosynaptex.py`.

Bootstrap CI (n = 500) is computed by resampling (topo, cost) pairs with
replacement and recomputing the Theil-Sen slope on each sample. The 2.5th
and 97.5th percentiles of the bootstrap distribution form the 95% CI.

A permutation p-value is computed by permuting the cost array 500 times and
counting how often the permuted slope is more extreme than the observed slope.

---

## Consequences

**Positive:**

- Theil-Sen is robust to up to ~29% outliers (breakdown point ≈ 0.29).
  OLS breakdown point is 0 — a single leverage point can dominate.
- The estimator is consistent and asymptotically normal, supporting
  valid CI inference.
- Bootstrap CI makes no normality assumption on residuals.
- The permutation p-value provides a non-parametric test of the null
  hypothesis that cost is independent of topology.
- Matches peer-reviewed precedent: Theil-Sen is standard for noisy
  biological power-law estimation (e.g., DFA slope estimation in HRV).

**Negative / trade-offs:**

- O(n^2) naively, O(n log n) with the Theil algorithm. For n < 5 000 pairs
  (all current substrates), runtime is negligible.
- Bootstrap + permutation adds ~500 regression calls per observe() tick.
  Mitigated by vectorised numpy resampling and the 16-tick warm-up window.
- Results differ slightly from OLS. The CI is wider than OLS CI under
  Gaussian noise — this is by design (conservative, honest uncertainty).

---

## Alternatives considered

| Method | Rejected because |
|--------|-----------------|
| OLS (scipy.stats.linregress) | Breakdown point = 0; single spike in topo or cost can produce |gamma| >> 1 |
| Huber regression | Parametric assumptions on residual distribution; harder to audit |
| Passing-Bablok | Designed for method-comparison (assumes both axes have error); not appropriate here — topo is controlled |
| LOWESS | Smoothing, not estimation of a global exponent |
| Sen's median slope only (no bootstrap) | Would not produce CI; CI is required by Invariant CI-REQUIRED |

---

## References

- `core/gamma.py::compute_gamma` — canonical implementation
- `core/bootstrap.py::bootstrap_summary` — bootstrap summary with permutation
- `evidence/gamma_ledger.json` — derived values
- Sen, P. K. (1968). Estimates of the regression coefficient based on
  Kendall's tau. *JASА*, 63(324), 1379–1389.
