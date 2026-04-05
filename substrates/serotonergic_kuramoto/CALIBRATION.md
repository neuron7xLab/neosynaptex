# Serotonergic Kuramoto — Calibration Report

> **Status:** T5 (calibrated model) in the NeoSynaptex provenance taxonomy.
> See `evidence/gamma_provenance.md` for the tier definition.
>
> **TL;DR.** The only free parameter in this substrate is the
> operational frequency bandwidth σ_op. With σ_op = 0.065 Hz the
> cross-concentration sweep yields γ ≈ 1.068, R² ≈ 0.58. This is not a
> knife-edge: γ ∈ [0.7, 1.3] holds over σ_op ∈ [0.058, 0.068] Hz — a
> contiguous 0.010 Hz basin (Δσ/σ ≈ 1.17×, 6 consecutive test grid
> points). Reproducible via `pytest tests/test_calibration_robustness.py -v`.

---

## Why calibration is necessary

The task specification fixes:

```
N = 64 oscillators
ω_i drawn from N(10, 2) Hz
K_eff = K_base · (1 − 0.7·c),  K_base = 2.0
dt = 1e-3,  10 000 steps per window
```

Taking the spec literally and converting "N(10, 2) Hz" to rad/s gives
σ_ω = 4π ≈ 12.57 rad/s, K_c = σ_ω·√(8/π) ≈ 20.05 rad/s, and a
coupling range K / K_c ∈ [0.06, 0.20] over c ∈ [0, 1]. The system is
then **deeply sub-critical at every concentration**: R ≲ 0.13, the
pair-count topo metric saturates near its combinatorial ceiling, and
the log-log fit of (topo, cost) is numerically ill-defined
(R² ≈ 0, γ sign-indeterminate).

To make the spec-literal `K_base = 2.0` land on metastability, we
rescale the frequency bandwidth. Everything else in the spec
(N = 64, K_base = 2.0, 10 000 steps, Gaussian ω, pair-count topo,
Σ|dθ_i/dt − ω_i| cost) is honoured verbatim.

## What the parameter means

`σ_op` is the **operational** Gaussian bandwidth used inside the
simulation (deterministic quantile draw). We distinguish it from the
*spec-literal* bandwidth of 2 Hz, which we retain as the physiological
reference (cortical alpha variance from Carhart-Harris et al. 2014).

The simulation is non-dimensional in time, so the absolute Hz value
of σ_op is a scaling convention; only the ratio K_base / K_c matters
for γ. With σ_op = 0.065 Hz (empirical K_c ≈ 0.645 rad/s),
K_base / K_c(c=0) ≈ 3.1, which puts the c = 0 end of the sweep at
super-critical coupling and the c = 1 end just below K_c. The sweep
therefore **crosses the Kuramoto phase transition** (at c ≈ 0.96),
producing a clean (topo, cost) scaling curve.

## Reference operating point

| Quantity | Value |
|----------|-------|
| σ_op | 0.065 Hz |
| K_c (empirical, quantile draw) | 0.645 rad/s |
| K_base / K_c (c = 0) | 3.099 |
| K_base / K_c (c = 1) | 0.930 |
| γ (sweep, seed = 42) | 1.0677 |
| R² (sweep) | 0.5826 |
| n sweep points | 20 |
| n phase IC per point | 4 |
| Regime | METASTABLE |

## Basin-width analysis

`tests/test_calibration_robustness.py` sweeps σ_op ∈ [0.054, 0.074] Hz
at 0.002–0.004 Hz resolution and records γ, R² at every point:

| σ_op (Hz) | γ | R² | In [0.7, 1.3]? |
|-----------|---|----|:-:|
| 0.054 | 0.580 | 0.58 | ✗ |
| 0.058 | 0.733 | 0.58 | ✓ |
| 0.060 | 0.819 | 0.58 | ✓ |
| 0.062 | 0.917 | 0.58 | ✓ |
| 0.065 | **1.068** | **0.58** | ✓ (reference) |
| 0.066 | 1.124 | 0.59 | ✓ |
| 0.068 | 1.244 | 0.59 | ✓ |
| 0.070 | 1.365 | 0.59 | ✗ |
| 0.074 | 1.616 | 0.59 | ✗ |

**Observed basin:** σ_op ∈ [0.058, 0.068] Hz — 6 contiguous grid
points, ratio σ_max / σ_min ≈ 1.17, absolute width 0.010 Hz.

**Monotonicity:** γ is smooth and monotone in σ_op across the full
sweep. Successive |Δγ| values between adjacent grid points stay
below 0.25 — there are no discontinuities. The dependence is
well-conditioned; there is no hidden bifurcation.

**R² stability:** R² stays at 0.58–0.59 across the entire sweep,
independent of whether γ is in-basin. The log-log fit quality is a
property of the sweep topology (finite-N folding near the critical
point), not of the calibration choice.

## Falsification conditions

The basin argument fails — and with it the T5 justification for this
substrate — if any of the following become true:

1. **Knife-edge collapse.** A finer resolution sweep reveals that the
   basin shrinks to a single grid point when σ_op step → 0.
   *Current result: basin is resolvable at 0.002 Hz step, width 0.010 Hz.*
2. **Seed fragility.** γ at the reference σ_op varies by more than 0.3
   across 10 construction seeds. (The phase IC averaging inside the
   adapter is designed to prevent this; if it fails, averaging is
   insufficient and the substrate should be demoted.)
3. **Topology hack.** Replacing the pair-count topo metric with a random
   permutation of its values across sweep points leaves γ unchanged.
   Tested in `tests/test_falsification_negative.py` (Phase 6).
4. **Non-monotonicity.** If a finer sweep reveals γ(σ) is not monotone
   on [0.04, 0.10] Hz, the "basin" interpretation breaks and becomes
   "random in-range hit".

## How to reproduce

```bash
# full calibration sweep (~80 s)
pytest tests/test_calibration_robustness.py -v -s

# single-point reference check (~8 s)
python3 -c "
from substrates.serotonergic_kuramoto.adapter import (
    SerotonergicKuramotoAdapter, _sweep_gamma,
)
a = SerotonergicKuramotoAdapter(concentration=0.5, seed=42)
print(_sweep_gamma(a))   # expect (1.0677..., 0.5826...)
"
```

## Honest assessment

A 1.17× basin is **modest, not generous**. A reviewer can reasonably
argue that a T5 substrate with a basin under 2× ratio should not count
as strong evidence for γ ≈ 1 and that the serotonergic Kuramoto entry
is best read as "a calibrated model that is consistent with the γ ≈ 1
hypothesis within a narrow window", not as "an independent witness".

The provenance taxonomy in `evidence/gamma_provenance.md` reflects
this: the serotonergic substrate is classified T5, explicitly below
the T1/T2/T3 witnesses, and the headline counts in that document only
include it under the "all tiers" row.

This is the honest state of the substrate. It stays in the repo
because (a) the physical model is canonical, (b) the calibration is
fully transparent, (c) the basin is resolvable at the 2 mHz level, and
(d) the same substrate is the target of several falsification controls
in Phase 6.

---

**Commit history of this calibration:**

| Commit | What changed |
|--------|--------------|
| `9552e82` | Initial serotonergic substrate, σ_op = 0.065 hard-coded |
| *(this)* | Expose `sigma_hz_op` as a constructor parameter; add basin test |
