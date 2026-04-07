# Diagnostic Mechanisms — Technical Reference

> **Audience:** researchers and engineers who need to understand the exact
> mathematical definitions of each diagnostic computed by `neosynaptex.py`.
>
> All ten mechanisms are computed in `Neosynaptex.observe()` and returned as
> fields of `NeosynaptexState`. The canonical implementation is in
> `neosynaptex.py`; the supporting math lives in `core/`.

---

## Overview

Each call to `observe()` runs ten diagnostic layers in sequence:

| # | Mechanism | Key output field | Section |
|---|-----------|-----------------|---------|
| 1 | Gamma scaling | `gamma_per_domain`, `gamma_mean` | [1](#1-gamma-scaling) |
| 2 | Jacobian / spectral radius | `sr_per_domain`, `spectral_radius` | [2](#2-jacobian--spectral-radius) |
| 3 | Spectral radius phase | `phase` | [3](#3-phase-classification) |
| 4 | Granger causality | `granger_graph` | [4](#4-granger-causality) |
| 5 | Anomaly isolation | `anomaly_score` | [5](#5-anomaly-isolation) |
| 6 | Phase portrait | `portrait` | [6](#6-phase-portrait) |
| 7 | Resilience | `resilience_score` | [7](#7-resilience) |
| 8 | Modulation signal | `modulation` | [8](#8-reflexive-modulation-signal) |
| 9 | Circuit breaker | `phase` (DEGENERATE guard) | [9](#9-circuit-breaker) |
| 10 | Universal scaling | `universal_scaling_p` | [10](#10-universal-scaling-test) |

---

## 1. Gamma Scaling

**Formula:**

```
log(K_t) = -gamma * log(C_t) + log(A)
```

where:
- `C_t` = `adapter.topo()` — topological complexity at tick t (must be > 0.01)
- `K_t` = `adapter.thermo_cost()` — thermodynamic cost at tick t (must be > 0.01)

**Estimator:** Theil-Sen slope on the window of (log C, log K) pairs (see
[ADR-003](../adr/ADR-003-theil-sen-estimator.md)). Negated because the relation
is K ~ C^(-gamma).

**Bootstrap CI:** 500 resamples of (log C, log K) pairs with replacement.
The 95% CI is the [2.5, 97.5] percentile interval of the bootstrap slope
distribution.

**R2:** Fraction of variance in log K explained by the linear fit in log-log
space. Gate: R2 >= 0.3 required for a METASTABLE verdict.

**EMA:** Exponential moving average of gamma with alpha = 0.3, stored in
`gamma_ema_per_domain`. Used for drift detection.

**Minimum pairs:** 5 valid (log C, log K) pairs required before gamma is
computed; returns NaN otherwise.

**Code:** `neosynaptex.py::_per_domain_gamma`, `core/gamma.py::compute_gamma`

---

## 2. Jacobian / Spectral Radius

The per-domain Jacobian approximates how each state variable responds to
changes in the other state variables over a sliding window.

**Construction:**

Given state matrix `X` of shape (T, n) where T = window length and n = number
of state keys, the Jacobian `J` is estimated as:

```
J = (X[1:].T @ X[:-1]) @ inv(X[:-1].T @ X[:-1])
```

which is the least-squares solution to `X[t+1] ≈ J @ X[t]`.

**Spectral radius:**

```
rho = max |eigenvalue(J)|
```

The spectral radius measures the largest amplification factor in the linear
approximation. Values:
- `rho < 0.80`: CONVERGING (damped dynamics)
- `0.80 <= rho <= 1.25`: METASTABLE (edge of stability)
- `1.25 < rho < 1.5`: DRIFTING (mild amplification)
- `rho >= 1.5`: DEGENERATE (explosive dynamics)

**Condition number gate:** If `cond(X[:-1]) > 1e6`, the Jacobian is
numerically ill-conditioned and `sr = NaN`.

**Cross-domain Jacobian (T3):** After 64 ticks, a cross-domain Jacobian
`J[i][j] = d(gamma_i)/d(state_mean_j)` is estimated via least-squares on
the trace of (state means, gammas). Returned in `cross_jacobian`.

**Code:** `neosynaptex.py::_per_domain_jacobian`

---

## 3. Phase Classification

Phase is assigned from the median spectral radius across all domains and the
gamma distribution. Phase changes require `_HYSTERESIS_COUNT = 3` consecutive
ticks in the new phase (hysteresis) to avoid flickering.

**Rules (in priority order):**

```
if degenerate_count >= 3:       phase = DEGENERATE
elif rho >= 1.5:                phase = DEGENERATE
elif |gamma_mean - 1.0| < 0.15 and 0.80 <= rho <= 1.25:
                                phase = METASTABLE
elif rho < 0.80:                phase = CONVERGING
elif gamma_mean > 1.15:         phase = DIVERGING
elif gamma_mean < 0.85:         phase = COLLAPSING
else:                           phase = DRIFTING
```

Initial phase before sufficient data: `INITIALIZING`.

**Code:** `neosynaptex.py::_classify_phase`

---

## 4. Granger Causality

Pairwise Granger causality is estimated between all domain pairs using a
VAR(1) model.

**Test statistic:**

For domains A -> B, the improvement in prediction of B when A's history is
included is:

```
F = (RSS_reduced - RSS_full) / RSS_full * (T - 2*p - 1) / p
```

where `RSS_reduced` is the residual sum of squares predicting B from its own
history only, `RSS_full` adds A's lagged values, T is the window size, and
p = 1 is the lag order.

The F-statistic is converted to a Granger "influence score" in [0, 1] via:

```
influence = F / (1 + F)
```

This gives a bounded score without requiring an F-distribution lookup.
Values near 1.0 indicate strong Granger causality; values near 0.0 indicate
no predictive relationship.

**Minimum requirement:** At least 3 finite values per domain after NaN removal.

**Code:** `neosynaptex.py::_granger_causality`

---

## 5. Anomaly Isolation

Leave-one-out anomaly score measures how much each domain deviates from the
cross-domain mean gamma.

**Formula:**

```
anomaly_score[d] = |gamma[d] - gamma_mean_excluding_d|
```

where `gamma_mean_excluding_d` is the mean gamma of all other domains.

A high anomaly score (> 0.3) indicates that domain `d` is the source of
cross-domain incoherence. Returned in `anomaly_score` dict.

**Code:** `neosynaptex.py::_anomaly_isolation`

---

## 6. Phase Portrait

The phase portrait characterises the geometry of the trajectory in
(gamma, spectral_radius) space over the observation window.

**Metrics computed:**

| Field | Formula | Meaning |
|-------|---------|---------|
| `area` | `ConvexHull(trajectory).volume` | Size of explored region in (gamma, rho) space |
| `recurrence` | fraction of points within distance 0.05 of centroid | How often system returns to typical region |
| `distance_to_ideal` | `sqrt((gamma_mean - 1)^2 + (rho_median - 1)^2)` | Euclidean distance from (1, 1) ideal |

Requires at least 3 finite (gamma, rho) pairs. Returns NaN fields if
insufficient data.

**Code:** `neosynaptex.py::_phase_portrait`

---

## 7. Resilience

Resilience measures the fraction of departures from METASTABLE that result
in a return to METASTABLE within the observation window.

**Formula:**

```
resilience_score = returns / departures   if departures > 0
                 = NaN                    if no departure yet
```

A departure is counted each time the phase transitions from METASTABLE to any
other phase. A return is counted each time it transitions back to METASTABLE.

A score of 1.0 means every perturbation was recovered; 0.0 means no recovery
was observed.

**Code:** `neosynaptex.py` — resilience tracking in `observe()`

---

## 8. Reflexive Modulation Signal

The modulation signal is a bounded correction vector that could be used to
nudge each domain adapter back toward the metastable regime.

**Formula:**

```
modulation[d] = clip(1.0 - gamma[d], -0.05, +0.05)
```

The signal is intentionally small (max ±5%) to prevent over-correction. It
is a diagnostic output, not an active control signal — adapters are not
required to use it.

**Code:** `neosynaptex.py::_modulation_signal`

---

## 9. Circuit Breaker

The circuit breaker prevents DEGENERATE phase from being incorrectly reversed
by hysteresis.

**Rule:**

If `spectral_radius >= _SR_DEGENERATE (1.5)`, an internal degenerate counter
is incremented. After `_DEGENERATE_COUNT = 3` consecutive ticks with
`rho >= 1.5`, the phase is permanently set to DEGENERATE and the hysteresis
candidate queue is cleared.

The phase can only leave DEGENERATE if `rho` drops below 1.25 for 3
consecutive ticks, resetting the counter.

**Code:** `neosynaptex.py` — degenerate counter in `observe()`

---

## 10. Universal Scaling Test

The universal scaling test checks whether all registered domains share the
same gamma exponent (universal scaling hypothesis).

**Method:**

Each domain's bootstrap gamma distribution (n = 500 samples) is compared to
the others using a permutation test:

1. Concatenate all bootstrap gamma samples from all domains.
2. Permute the concatenated array 500 times.
3. For each permutation, compute the variance across domain means.
4. p-value = fraction of permuted variances >= observed variance.

A low p-value (p < 0.05) indicates the domains have significantly different
gamma values — the universal scaling hypothesis is rejected.
A high p-value (p > 0.05) is consistent with universal scaling (all domains
share the same exponent within noise).

**Output:** `universal_scaling_p` in `NeosynaptexState`. Returned as NaN if
fewer than 2 domains have valid bootstrap samples.

**Code:** `neosynaptex.py::_universal_scaling_test`
