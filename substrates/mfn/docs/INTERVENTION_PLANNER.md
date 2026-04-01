# Causal Intervention Planner (CIP)

## Overview

The CIP answers: **"What parameter changes would move this system toward a target regime?"**

It searches over a constrained lever space, evaluates each candidate through the
full MFN pipeline (simulate→extract→detect→forecast→compare), validates via the
causal gate, and returns a Pareto-optimal intervention plan.

## Quick Start

```python
import mycelium_fractal_net as mfn

seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=24, seed=42))
plan = mfn.plan_intervention(
    seq,
    target_regime="stable",
    allowed_levers=["gabaa_concentration", "serotonergic_gain"],
    budget=5.0,
)

if plan.has_viable_plan:
    best = plan.best_candidate
    print(f"Score: {best.composite_score:.4f}")
    for change in best.proposed_changes:
        print(f"  {change.name}: {change.current_value} → {change.proposed_value}")
```

## Fluent API

```python
plan = seq.stabilize(target_regime="stable", budget=3.0)
```

## Available Levers

| Lever | Default | Bounds | Cost/unit | Plausibility |
|-------|---------|--------|-----------|-------------|
| gabaa_concentration | 0.0 | [0, 100] | 0.1 | pharmacological |
| gabaa_shunt_strength | 0.0 | [0, 1] | 0.5 | pharmacological |
| serotonergic_gain | 0.0 | [0, 0.3] | 1.0 | pharmacological |
| serotonergic_plasticity | 1.0 | [0.5, 3.0] | 0.3 | pharmacological |
| diffusion_alpha | 0.18 | [0.05, 0.24] | 2.0 | computational |
| spike_probability | 0.25 | [0, 1] | 0.2 | physiological |
| noise_std | 0.0 | [0, 0.01] | 0.1 | computational |

## Scoring Function

Composite score (lower is better):

| Component | Weight | Description |
|-----------|--------|-------------|
| regime_distance | 0.25 | Distance from target regime |
| anomaly_reduction | 0.20 | How much anomaly score decreased |
| intervention_cost | 0.15 | Normalized cost within budget |
| structural_drift | 0.15 | How much structure changed |
| causal_penalty | 0.10 | Penalty for causal gate degradation |
| uncertainty | 0.10 | Forecast uncertainty |
| robustness | 0.05 | Stability under perturbation |

## Architecture

```
plan_intervention()
  ├── build_candidates()      # Search space generation
  ├── run_counterfactual()    # Full pipeline per candidate
  ├── compute_composite_score()  # Multi-objective scoring
  ├── filter_candidates()     # Causal gate filtering
  ├── evaluate_robustness()   # Perturbation testing
  └── compute_pareto_front()  # Multi-objective selection
```

## Assumptions & Limits

1. **Counterfactual = re-simulation**: Each candidate runs the full pipeline.
   For 32 candidates at 32x32, expect ~1-2 seconds total.
2. **Budget is abstract**: Cost units are relative, not monetary.
3. **Levers are independent**: No interaction effects modeled between levers.
4. **Causal gate is mandatory**: No candidate can bypass causal validation.
5. **Deterministic**: Same seed → same plan.
