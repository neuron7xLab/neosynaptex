# Architecture Audit — MFN v0.1.0

**Date:** 2026-03-28
**Status:** Post-audit, structural debt documented

## Module Map (19 packages)

```
mycelium_fractal_net/
├── core/              # R-D engine, detect, diagnose, forecast, thermodynamic kernel
├── analytics/         # 40+ analytics: TDA, entropy, fractals, morphology, invariants
├── types/             # 18+ frozen dataclasses (canonical data contracts)
├── neurochem/         # GNC+ (7 axes × 9 theta), OmegaOrdinal, A_C operator
├── bio/               # Physarum, FHN, chemotaxis, anastomosis, Levin pipeline
├── neural/            # AdEx spiking network, STDP, criticality
├── interpretability/  # READ-ONLY: feature extraction, attribution, gamma diagnostics
├── self_reading/      # READ-ONLY + Recovery → {Θ, PID}: 5-layer introspection
├── tau_control/       # READ-ONLY + Transformation → {C}: identity preservation
├── experiments/       # Phase 3 real simulation evidence
├── intervention/      # Pareto search, levers, counterfactual
├── integration/       # FastAPI server, WebSocket, connectors
├── pipelines/         # Forecasting, reporting, scenarios
├── security/          # Audit, encryption, hardening
├── numerics/          # Grid ops, fused kernels
├── adapters/          # Field loading
├── crypto/            # FROZEN: key exchange, signatures
├── signal/            # FROZEN: preprocessor, denoising
└── model_pkg/         # PyTorch neural model (lazy)
```

## Dependency Direction (canonical)

```
types ← core ← analytics ← {interpretability, self_reading, tau_control}
                   ↑
              bio, neural, neurochem
```

Forbidden directions:
- interpretability → core.simulate (must not trigger simulation)
- self_reading → core.engine (read-only except recovery.py)
- tau_control → core.simulate (read-only except transformation.py)
- types → core (types are leaf-level)

## Import Cycles (11 detected)

| Cycle | Severity | Root Cause |
|-------|----------|------------|
| analytics ↔ core | HIGH | core.detect imports analytics.morphology; analytics imports core.extract |
| analytics ↔ types | LOW | types used at runtime in both; TYPE_CHECKING would break |
| core ↔ types | LOW | Same pattern — runtime dependency both ways |
| core ↔ intervention | MEDIUM | core.diagnose imports intervention.plan_intervention |
| core ↔ numerics | LOW | numerics.grid_ops used by core; core types used by numerics |
| bio ↔ core | MEDIUM | bio mechanisms import core simulation primitives |
| core ↔ pipelines | LOW | pipelines consume core, core.report uses pipeline helpers |
| pipelines ↔ types | LOW | Runtime dependency |
| config ↔ config_validation | LOW | Intentional co-dependency |
| api ↔ api_v1 | LOW | API version delegation |

**Mitigation:** Most cycles are LOW severity — runtime co-dependencies between
data layer (types) and logic (core/analytics). Breaking them requires major API
redesign not justified by current risk. HIGH cycles are documented for future refactor.

## Duplicated Contracts (10 class names)

| Class | Locations | Resolution |
|-------|-----------|------------|
| FeatureVector | analytics/fractal_features, analytics/legacy_features, interpretability/feature_extractor | **3 distinct types serving different purposes**: legacy (18-dim), fractal (18-dim wrapper), interpretability (4-group dict). NOT true duplicates — different semantics. |
| BoundaryCondition | core/reaction_diffusion_config, numerics/grid_ops, types/field | **Genuine triplicate.** types/field.py should be canonical. |
| ScenarioConfig | experiments/scenarios, pipelines/scenarios | Different schemas for different purposes. |
| STDPPlasticity | core/stdp, neural/stdp | FROZEN module (core) + active (neural). |
| Others (5) | Various | Minor: config validation, retry, dataset meta. |

## Read/Write Boundaries

| Module | Access | Write Target |
|--------|--------|-------------|
| interpretability/* | READ-ONLY | — |
| self_reading/{self_model,coherence,interpretability,phase_validator} | READ-ONLY | — |
| self_reading/recovery.py | WRITE | Θ, PID |
| tau_control/{all except transformation.py} | READ-ONLY | — |
| tau_control/transformation.py | WRITE | C (meta-rules) |
| core/* | READ-WRITE | Simulation state |
| analytics/* | READ-ONLY | — |

## Key Metrics

| Metric | Value |
|--------|-------|
| Python files | 256 |
| Total classes | 464 |
| Unique class names | 452 |
| Import cycles | 11 |
| Cross-package edges | 84 |
| dict[str, Any] in core | 127 |
| Total __all__ symbols | 526 |
| Tests | 2,815 pass |
| Import contracts | 10 |

## Structural Debt (prioritized)

1. **BoundaryCondition triplicate** — should consolidate to types/field.py
2. **dict[str, Any] in 127 places** — gradual typed contract migration needed
3. **analytics ↔ core cycle** — HIGH severity, would require adapter layer
4. **integration __all__ = 114** — overly broad public surface

## Recommendation

The architecture is sound for a research platform. The identified debt is
manageable and does not block scientific publication or deployment.
Priority: consolidate BoundaryCondition, then gradual dict→typed migration.
