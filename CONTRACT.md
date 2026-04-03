# neosynaptex -- Engineering Contract

**Version:** 3.0.0
**Author:** Yaroslav Vasylenko (neuron7xLab)
**Status:** Production-grade reference implementation

---

## 1. Purpose

neosynaptex is the reflexive interface layer for the Neuron7x Fractal Intelligence (NFI) platform.
It does not simulate, generate, or control. It **observes** four subsystems and **diagnoses** their
collective coherence through seven independent mechanisms.

The design principle: **Observer IS the Medium.** The system's observation of itself becomes
part of the dynamics it observes, through bounded modulation signals fed back to adapters.

---

## 2. Invariants

Violation of any invariant constitutes a build failure.

| # | Invariant | Enforcement |
|---|-----------|-------------|
| I-1 | Gamma is derived, never stored | `observe()` recomputes every call; no `gamma` attribute on `Neosynaptex` |
| I-2 | STATE != PROOF | `NeosynaptexState` is `frozen=True`; `phi` and `diagnostic` are independent copies |
| I-3 | Zero external deps beyond numpy/scipy | No sklearn, torch, pandas, plotly |
| I-4 | Bounded modulation | `\|mod\| <= 0.05` enforced by `np.clip` |
| I-5 | ASCII identifiers | No Cyrillic character with ord > 127 in any non-comment code |

---

## 3. Data Flow

```
                    ┌───────────────────────────────────────┐
                    │           Neosynaptex.observe()       │
                    │                                       │
  Adapters ────────►│  1. Collect Phi(t) from 4 domains     │
  (state,           │  2. Per-domain Jacobian + cond gate   │
   topo,            │  3. Per-domain gamma + bootstrap CI   │
   thermo_cost)     │  4. dg/dt (convergence rate)          │
                    │  5. Permutation test (universal H0)   │
                    │  6. Granger causality (who->whom)     │
                    │  7. Anomaly isolation (who is outlier) │
                    │  8. Phase portrait (trajectory topo)  │
                    │  9. Phase + hysteresis                │
                    │  10. Resilience (return rate)          │
                    │  11. Modulation signal (bounded)       │
                    │                                       │
                    └──────────┬────────────────────────────┘
                               │
                               ▼
                    ┌───────────────────────┐
                    │   NeosynaptexState    │
                    │   (frozen, immutable) │
                    └───────────────────────┘
```

---

## 4. Domain Adapter Contract

Each subsystem implements the `DomainAdapter` protocol:

```
domain        : str           # unique ASCII name, e.g. "spike"
state_keys    : List[str]     # ordered, max 4 keys
state()       : Dict[str, float]  # current state (may contain NaN)
topo()        : float         # topological complexity (> 0 or NaN)
thermo_cost() : float         # thermodynamic cost (> 0 or NaN)
```

### Power-law contract

The adapter MUST provide `topo` and `thermo_cost` such that:

```
thermo_cost ~ A * topo^(-gamma)
```

when the subsystem operates near its critical point. The scaling exponent `gamma` is what
neosynaptex estimates via Theil-Sen regression. If this relationship does not hold, the
gamma estimate will be gated out (R^2 < 0.5 or range < 0.5).

### Domain specifications

| Domain | Adapter | State keys | topo semantics | cost semantics |
|--------|---------|------------|----------------|----------------|
| spike | BN-Syn | sigma, firing_rate, coherence | network connectivity | spike energy |
| morpho | MFN+ | d_box, beta0, beta1, delta_h | topological features (Betti sum) | entropy change |
| psyche | PsycheCore | free_energy, kuramoto_r | oscillator count | variational free energy |
| market | mvstack | regime, w1_distance, ricci_curvature | graph connectivity | Wasserstein transport cost |

---

## 5. Formulas

### 5.1 Gamma estimation (Theil-Sen + bootstrap)

```
Input: arrays topo[1..W], cost[1..W] from domain buffer

1. Filter: keep pairs where topo > 0, cost > 0, both finite
2. Gate: require >= 5 valid pairs
3. Gate: require ptp(log(topo)) >= 0.5  (rejects stationary data)
4. Regression: slope, intercept = theilslopes(log(cost), log(topo))
   gamma = -slope
5. Gate: require R^2 >= 0.5
6. Bootstrap CI: 200 resamples, percentile [2.5%, 97.5%]
```

### 5.2 Gamma dynamics

```
dg/dt = theilslopes(gamma_mean_trace[-W:], arange(W))
```

Negative dg/dt with gamma > 1.0 = converging toward criticality.

### 5.3 Universal scaling test

```
H0: all domains share the same gamma distribution
Method: permutation test (500 iterations)
Statistic: variance of group means
p-value: (count_permuted_stat >= observed_stat + 1) / (N + 1)
```

### 5.4 Per-domain Jacobian

```
Input: state history (W, n_domain) from domain buffer

1. Mask NaN rows
2. dPhi = diff(clean_states)
3. J_local = lstsq(Phi_prev[:-1], dPhi[1:]).T
4. Gate: condition_number(Phi_prev) < 1e6
5. A_transition = J_local + I
6. sr = max|eigenvalues(A_transition)|
```

### 5.5 Granger causality

```
For each pair (source, target):
  Restricted model: gamma_target(t) ~ gamma_target(t-1)
  Full model:       gamma_target(t) ~ gamma_target(t-1) + gamma_source(t-1)
  F = ((RSS_restricted - RSS_full) / df1) / (RSS_full / df2)
```

### 5.6 Anomaly isolation

```
For each domain d:
  coherence_without_d = 1 - CV(gammas excluding d)
  coherence_with_all  = 1 - CV(all gammas)
  anomaly_score(d) = clamp((without - with) / (1 - with), 0, 1)
```

### 5.7 Phase portrait

```
Points: (gamma_mean(t), sr(t)) for t in trace

area            = ConvexHull volume of points  (small = fixed point)
recurrence      = fraction of points within epsilon of any prior point
distance_ideal  = mean distance to (1.0, 1.0)
```

### 5.8 Phase determination

```
Raw phase from sr and dg/dt:
  sr = NaN                              -> INITIALIZING
  sr > 1.5 for 3+ ticks                -> DEGENERATE (sentinel)
  sr > 1.20                             -> DIVERGING
  sr < 0.80                             -> COLLAPSING
  sr in [0.80, 1.20] + dg/dt -> 1.0    -> CONVERGING
  sr in [0.80, 1.20] + dg/dt away 1.0  -> DRIFTING
  sr in [0.80, 1.20] + dg/dt ~ 0       -> METASTABLE

Hysteresis: phase transition requires 3 consecutive ticks in candidate phase.
```

### 5.9 Resilience

```
resilience = n_returns / n_departures

departure: system was METASTABLE, now is not
return:    system was not METASTABLE, now is (and departures > 0)
```

### 5.10 Modulation signal

```
mod(domain) = clip(-0.05 * (gamma_domain - 1.0) * sign(dg/dt), -0.05, +0.05)
```

Positive mod = strengthen domain (gamma too low and falling).
Negative mod = dampen domain (gamma too high and rising).

---

## 6. State Schema

```python
@dataclass(frozen=True)
class NeosynaptexState:
    t: int                                          # tick counter
    phi: np.ndarray                                 # concatenated state vector (copy)
    phi_per_domain: Dict[str, np.ndarray]           # per-domain state vectors (copies)

    gamma_per_domain: Dict[str, float]              # gamma or NaN
    gamma_ci_per_domain: Dict[str, Tuple[float, float]]  # (ci_low, ci_high) or NaN
    gamma_mean: float                               # mean of valid gammas
    gamma_std: float                                # std of valid gammas
    cross_coherence: float                          # 1 - CV(gamma_valid)

    dgamma_dt: float                                # convergence rate
    gamma_ema_per_domain: Dict[str, float]          # exponential moving average

    universal_scaling_p: float                      # permutation test p-value

    sr_per_domain: Dict[str, float]                 # spectral radius
    cond_per_domain: Dict[str, float]               # condition number
    spectral_radius: float                          # median of valid sr

    phase: str                                      # system phase

    anomaly_score: Dict[str, float]                 # leave-one-out score
    granger_graph: Dict[str, Dict[str, float]]      # directed F-stat graph
    portrait: Dict[str, float]                      # area, recurrence, distance_to_ideal
    resilience_score: float                         # returns / departures

    modulation: Dict[str, float]                    # bounded reflexive signal
    diagnostic: Dict                                # full internal details
```

---

## 7. Quality Gates

| Gate | Criterion |
|------|-----------|
| Gamma range gate | `ptp(log(topo)) >= 0.5` (rejects stationary data) |
| Gamma R^2 gate | `R^2 >= 0.5` (rejects noise) |
| Jacobian cond gate | `cond(X) < 1e6` (rejects ill-conditioned estimates) |
| Min pairs gate | `>= 5` valid (topo, cost) pairs for gamma |
| Hysteresis gate | 3 consecutive ticks to confirm phase transition |
| Modulation bound | `\|mod\| <= 0.05` enforced by clip |

---

## 8. Proof Bundle Schema

`export_proof()` returns JSON-serializable dict:

```
{
  version: str,
  ticks: int,
  gamma: {per_domain: {name: {value, ci, r2, ema}}, mean, std, dgamma_dt, universal_scaling_p},
  jacobian: {name: {sr, cond}},
  phase: str,
  anomaly: {name: score},
  granger: {source: {target: F}},
  portrait: {area, recurrence, distance_to_ideal},
  resilience: float,
  modulation: {name: float},
  coherence: float,
  verdict: "COHERENT" | "INCOHERENT" | "PARTIAL"
}
```

Verdict logic:
- **COHERENT**: `cross_coherence > 0.85` AND phase in `{METASTABLE, CONVERGING}`
- **INCOHERENT**: phase in `{DEGENERATE, DIVERGING}`
- **PARTIAL**: everything else

---

## 9. v2 Roadmap (not yet implemented)

- NeedTensor `N(t) = -grad_theta(F)` (requires differentiable PsycheCore)
- Cross-domain Jacobian (requires window >= 64)
- Adaptive window sizing based on gamma CI width
- Real-time streaming adapter (asyncio)
- Proof chain: cryptographic hash linking successive proof bundles

---

*"The beam is not ahead. It is where the tunnels meet."*
