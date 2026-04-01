# Neuro-Informational Control Substrate (NICS) Specification

**Document Version:** 1.0.0
**Status:** Draft (Reference-Class)

## Purpose

NICS defines a **system class** for neuro-inspired, real-time information processing. It specifies the minimal operational substrate that others can instantiate for different domains (agents, CI governance, workflow orchestration) while preserving governance-dominant control and bounded adaptation.

## System Class Definition

**NICS** is a real-time information-processing substrate with:
- hierarchical state,
- controlled plasticity,
- bounded adaptation,
- explicit error-driven modulation,
- and governance-dominant execution.

This is a **reference class**, not a single product implementation.

## Dominance Order (Non-Negotiable)

1. **Governance** (inhibition + long-term objectives)
2. **Adaptation** (bounded, error-driven modulation)
3. **Execution** (bounded action selection)

## Canonical Dataflow

```
input_signals
  → state_snapshot
  → prediction_error
  → modulation_state
  → inhibition_result
  → selected_action
  → decision_trace
```

## Required Subsystems

1. **Signal Normalization**
   - deterministic bounds and modality typing.
2. **Prediction Error Engine**
   - local + propagated + global error, explicitly bounded.
3. **Neuromodulatory Control**
   - bounded parameter updates driven only by error signals.
4. **Governance Computation**
   - inhibitory computation over action space with veto power.
5. **Memory System**
   - decay + consolidation + capacity limits.
6. **Decision Trace**
   - deterministic artifact emitted for every decision.

## Non-Goals (Explicit)

NICS is **not**:
- conscious,
- agentic in a human sense,
- self-directed without bounds,
- creative without constraints,
- a replacement for policy governance.

## Reference Implementation

MLSDM is the first instance of NICS, used to demonstrate:
- bounded memory control,
- prediction-error-driven adaptation,
- governance-dominant action selection,
- and deterministic decision traces.
