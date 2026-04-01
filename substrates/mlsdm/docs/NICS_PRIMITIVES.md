# NICS Primitive Definitions

**Document Version:** 1.0.0
**Status:** Draft (Reference-Class)

## Purpose

Defines the canonical primitives that make up the NICS instruction set. Each primitive has allowed transformations, forbidden states, and invariants.

## Primitive: State
- **Role:** hierarchical snapshot of system memory, policy, and modulation.
- **Allowed transformations:** decay, consolidation, bounded updates.
- **Forbidden states:** unbounded growth; NaN values; missing invariants.
- **Invariant:** memory usage ≤ configured max.

## Primitive: Signal
- **Role:** normalized inputs and internal telemetry.
- **Allowed transformations:** normalization, aggregation, gating.
- **Forbidden states:** untyped, out-of-range, or unverifiable signals.
- **Invariant:** every signal ∈ [0, 1] (after normalization).

## Primitive: Error
- **Role:** sole driver of adaptation.
- **Allowed transformations:** local computation, propagation, aggregation.
- **Forbidden states:** adaptation without attributable error.
- **Invariant:** bounded error accumulation with saturation.

## Primitive: Modulator
- **Role:** bounded control parameters (exploration, learning, consolidation, strictness).
- **Allowed transformations:** error-driven, decayed updates; homeostatic braking.
- **Forbidden states:** bypassing governance; unbounded drift.
- **Invariant:** modulators remain within configured ranges.

## Primitive: Inhibitor (Governance)
- **Role:** veto power over action space.
- **Allowed transformations:** rule evaluation, risk gating, veto enforcement.
- **Forbidden states:** bypass or override by adaptive subsystems.
- **Invariant:** `allow_execution=false` ⇒ action blocked.

## Primitive: Memory
- **Role:** bounded, multi-level storage with decay and consolidation.
- **Allowed transformations:** update, retrieval, consolidation, eviction.
- **Forbidden states:** unbounded accumulation; missing decay.
- **Invariant:** capacity constraints always hold.

## Primitive: Policy
- **Role:** versioned governance constraints and objectives.
- **Allowed transformations:** explicit, audited updates with impact analysis.
- **Forbidden states:** silent or implicit change.
- **Invariant:** policy updates are versioned and auditable.

## Primitive: Action
- **Role:** bounded execution output under governance constraints.
- **Allowed transformations:** selection from permitted action set.
- **Forbidden states:** execution without inhibition clearance.
- **Invariant:** every action has a decision trace.
