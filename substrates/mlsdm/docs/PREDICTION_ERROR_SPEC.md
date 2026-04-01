# Prediction Error Specification

**Document Version:** 1.0.0
**Status:** Draft (vNext)

## Purpose

This document defines the prediction error signals used as first-class drivers for adaptation.

## Definitions

### Layered Error Signals
All errors are normalized to **[0, 1]** and computed deterministically.

- **Perception Error (L1):** mismatch between expected input constraints and observed prompt characteristics.
- **Memory Retrieval Error (L2):** mismatch between required context and retrieved memory coverage.
- **Policy Execution Error (L3):** failure to pass governance constraints (rejection or forced fallback).

### Error Vector

```
E = (e_perception, e_memory, e_policy)
```

### Total Error

```
E_total = clamp(0.4 * e_perception + 0.3 * e_memory + 0.3 * e_policy, 0, 1)
```

### Propagation Rules
Propagation is bounded and explicit:

```
L1 → L2 = clamp(0.6 * e_perception)
L2 → L3 = clamp(0.6 * e_memory)
L1 → L3 = clamp(0.3 * e_perception + 0.2 * e_memory)
Policy Gate = clamp(e_policy)
```

## Error Triggers

- **Perception Error Trigger:** moral pre-check score diverges from requested moral threshold.
- **Memory Error Trigger:** insufficient retrieved context items relative to requested context_top_k.
- **Policy Error Trigger:** rejected_at ≠ None OR error ≠ None.

## Invariants

1. **Bounded Error:** each signal is always in [0, 1].
2. **Bounded Accumulation:** cumulative error saturates at a fixed maximum and decays over time.
3. **Traceability:** every error is logged in the Decision Trace artifact.
4. **No Silent Drift:** accumulator saturation is surfaced in observability.

## Implementation References

- `src/mlsdm/cognition/prediction_error.py` implements signal computation and accumulation.
- `src/mlsdm/engine/neuro_cognitive_engine.py` emits prediction errors in decision traces.
