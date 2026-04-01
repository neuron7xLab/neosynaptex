# BN-Syn Temperature Ablation Hypothesis

**Status**: NON-NORMATIVE experimental document  
**Version**: 2.0  
**Date**: 2026-01-26

This document describes a falsifiable hypothesis linking temperature-controlled plasticity gating to consolidation stability in dual-weight synapses.

---

## Hypothesis H1: Temperature-Controlled Consolidation Stability

**Statement**: Phase-controlled temperature gating improves consolidation stability in DualWeights compared to fixed temperature regimes, while maintaining active protein synthesis and consolidation.

**Rationale**: The temperature schedule (`TemperatureSchedule`) modulates plasticity via `gate_sigmoid(T, Tc, gate_tau)`, which gates the effective learning rate applied to `DualWeights.w_fast`. Piecewise cooling with a warmup phase (`T = T0` for warmup steps, then slow geometric cooling `T0 → Tmin` with `alpha ≈ 0.9995`) provides a controlled annealing process that reduces variance in final consolidated weights (`w_total`) across independent trials while preserving consolidation activity (protein synthesis and w_cons accumulation).

---

## Experimental Design (v2)

### Conditions

Four temperature regimes are tested under identical synthetic input patterns:

| Condition | Description | Temperature Profile |
|-----------|-------------|---------------------|
| **cooling_piecewise** | Piecewise cooling with warmup | T(step) = T0 for step < 500, then T(step) = max(Tmin, T(step-1) * alpha) |
| **fixed_high** | Fixed high temperature | T(step) = T0 for all steps |
| **fixed_low** | Fixed low temperature | T(step) = Tmin for all steps |
| **random_T** | Random temperature | T(step) ~ Uniform(Tmin, T0), seeded |

### Synthetic Input Protocol

> **PROVISIONAL / NOT INDEPENDENTLY VALIDATED**: Synthetic input patterns are used as controlled proxies for this experiment and do not by themselves establish external validity.

- **Input pattern**: Deterministic pseudo-random pulses to `fast_update` using seeded `numpy.random.Generator`.
- **Matrix size**: (10, 10) synapse matrix (configurable parameter).
- **Steps**: 5000 consolidation steps (default configuration).
- **Seeds**: 20 independent trials per condition (validation run); 5 for smoke tests.
- **DualWeightParams**: Default parameters from `bnsyn.config.DualWeightParams`.
- **TemperatureParams**: T0=1.0, Tmin=1e-3, alpha=0.9995, Tc=0.1, gate_tau=0.02, warmup_steps=500.

### Effective Update Rule

At each step, the temperature gate modulates the fast weight update:

```
gate = gate_sigmoid(T, Tc, gate_tau)
effective_update = gate * fast_update
DualWeights.step(dt_s, params, effective_update)
```

---

## Metrics

Stability metrics are computed across the `seeds` trials for each condition:

| Metric ID | Definition | Acceptance Target |
|-----------|------------|-------------------|
| **stability_w_total_var_end** (PRIMARY) | Variance across seeds of final `mean(w_total)` | Lower for cooling vs fixed_high by ≥10% |
| **stability_w_cons_var_end** (SECONDARY) | Variance across seeds of final `mean(w_cons)` | Lower for cooling vs fixed_high (when consolidation active) |
| **protein_mean_end** | Final protein level (mean across seeds) | ≥ 0.90 for cooling and fixed_high (non-trivial consolidation gate) |
| **w_cons_mean_final** | Final consolidated weight (mean across seeds) | abs(value) ≥ 1e-4 for cooling and fixed_high (non-trivial consolidation gate) |
| **tag_activity_mean** | Mean fraction of active tags over time | Reported (no specific target) |

### Acceptance Criterion

**H1 is supported** if ALL of the following hold:

1. **Non-trivial consolidation gates** (both must pass):
   - `cooling_piecewise`: `protein_mean_end >= 0.90` AND `abs(w_cons_mean_final) >= 1e-4`
   - `fixed_high`: `protein_mean_end >= 0.90` AND `abs(w_cons_mean_final) >= 1e-4`

2. **Stability improvement**:
   - `cooling_piecewise` produces **lower** `stability_w_total_var_end` than `fixed_high` by at least 10% (relative reduction)

**H1 is refuted** if:
- Either cooling or fixed_high fails the non-trivial consolidation gate (indicates consolidation was trivially suppressed)
- OR the stability improvement criterion is not met

**Rationale for gates**: The non-trivial consolidation gates prevent "trivial wins" where cooling achieves stability by completely shutting down plasticity and consolidation. We require that both cooling and fixed_high conditions demonstrate active protein synthesis (protein ≥ 0.90) and meaningful consolidated weight accumulation (|w_cons| ≥ 1e-4), ensuring that stability improvements come from controlled dynamics rather than plasticity suppression.

---

## Reproduce

### Installation

```bash
pip install -e ".[dev,test,viz]"
```

### Run flagship experiment (v2)

```bash
# Full validation run (seeds=20, ~2-5 minutes)
python -m experiments.runner temp_ablation_v2

# Fast smoke test (seeds=5)
python -m experiments.runner temp_ablation_v2 --seeds 5 --out results/_smoke
```

### Generate visualizations

```bash
python -m scripts.visualize_experiment --run-id temp_ablation_v2
```

### Verify hypothesis

```bash
python -m experiments.verify_hypothesis docs/HYPOTHESIS.md results/temp_ablation_v2
```

---

## Expected Outputs

- **results/temp_ablation_v2/**: Per-condition JSON files with per-seed metrics + aggregates.
- **results/temp_ablation_v2/manifest.json**: Reproducibility manifest (git commit, params, hashes).
- **figures/temp_ablation_v2/hero.png**: Stability curve comparison across conditions.
- **figures/temp_ablation_v2/temperature_vs_stability.png**: Temperature profile vs stability metrics.
- **figures/temp_ablation_v2/tag_activity.png**: Tag activity over time by condition.
- **figures/temp_ablation_v2/comparison_grid.png**: Multi-panel comparison grid.

---

## References

- SPEC P1-5: Temperature schedule and gating (`src/bnsyn/temperature/schedule.py`).
- SPEC P1-6: Dual-weight consolidation (`src/bnsyn/consolidation/dual_weight.py`).
- SPEC P2-9: Determinism protocol (`src/bnsyn/rng.py`).

---

## Appendix: Version 1 Baseline

### temp_ablation_v1 (Baseline Demonstration)

The original v1 experiment (`temp_ablation_v1`) demonstrated extreme stability improvement (99.996% variance reduction) but achieved this by essentially disabling consolidation through rapid cooling (alpha=0.95). While scientifically valid, this represents a "trivial win" where stability comes at the cost of plasticity shutdown.

**v1 Parameters**:
- alpha=0.95 (rapid cooling)
- No warmup phase
- Hardcoded (10,10) matrix

**v1 Results**:
- Massive variance reduction but protein synthesis largely suppressed
- Demonstrates the plasticity-stability tradeoff
- Serves as proof-of-concept for temperature gating mechanism

**v2 Improvements**:
- Slower cooling (alpha=0.9995) to maintain consolidation activity
- Warmup phase (500 steps at T0) to allow initial protein synthesis
- Non-trivial consolidation gates to verify active consolidation
- Configurable matrix_size parameter

v1 results remain available in `results/temp_ablation_v1/` for reference, but **v2 is the flagship experiment** demonstrating stability improvement with active consolidation.

---

## Notes

This document is **non-governed** and does not use normative keywords (`must`, `shall`, `required`, `guarantee`) except in clearly marked quotations or references to governed documents. It describes an experimental protocol for generating evidence artifacts.
