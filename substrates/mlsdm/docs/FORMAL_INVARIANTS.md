# Formal Invariants

## Overview

This document defines the **formal invariants** for the MLSDM Governed Cognitive Memory system. These invariants serve as mathematical and logical contracts that must hold throughout system execution, reflecting safety and control expectations from ISO/IEC 42001 and related governance frameworks [@iso2023_42001; @ieee2020_7010]. They are verified through property-based testing using Hypothesis.

---

## 1. LLMWrapper

### 1.1 Safety Invariants (what must NEVER happen)

**INV-LLM-S1: Memory Bounds** [@davies2018_loihi]
- **Statement**: Total memory usage MUST NOT exceed 1.4 GB under any circumstances
- **Formal**: `memory_usage() ≤ 1.4 * 10^9 bytes`
- **Rationale**: Prevents unbounded memory growth and enables edge deployment

**INV-LLM-S2: Capacity Constraint**
- **Statement**: Number of vectors in memory MUST NOT exceed configured capacity
- **Formal**: `|memory_vectors| ≤ capacity`
- **Rationale**: Enforces hard limits on memory system size

**INV-LLM-S3: Vector Dimensionality**
- **Statement**: All embeddings MUST have consistent dimensionality
- **Formal**: `∀v ∈ memory: dim(v) = configured_dim`
- **Rationale**: Prevents dimension mismatch errors in similarity calculations

**INV-LLM-S4: Circuit Breaker State Transitions**
- **Statement**: Circuit breaker MUST NOT transition from OPEN to CLOSED without passing through HALF_OPEN
- **Formal**: `state_transition(OPEN → CLOSED) ⟹ ∃t: state(t) = HALF_OPEN`
- **Rationale**: Ensures proper recovery testing before resuming operations

### 1.2 Liveness Invariants (what must ALWAYS happen)

**INV-LLM-L1: Embedding Generation**
- **Statement**: Given valid input and CLOSED circuit breaker, embedding function MUST eventually return a vector
- **Formal**: `valid_input ∧ state = CLOSED ⟹ ◇(embedding_returned)`
- **Rationale**: System must make progress on valid requests

**INV-LLM-L2: Retry Exhaustion Handling**
- **Statement**: After retry attempts exhausted, system MUST return structured error response
- **Formal**: `retries_exhausted ⟹ error_response.type ∈ {timeout, circuit_open, unknown}`
- **Rationale**: Prevents infinite hanging on failures

**INV-LLM-L3: Memory Overflow Handling**
- **Statement**: When capacity reached, system MUST evict oldest/least-relevant entries
- **Formal**: `|memory| = capacity ∧ insert(v) ⟹ ∃v_old: remove(v_old) ∧ |memory| = capacity`
- **Rationale**: Ensures bounded memory with graceful degradation

### 1.3 Metamorphic Invariants (input-output relationships)

**INV-LLM-M1: Embedding Stability**
- **Statement**: Identical inputs produce identical embeddings (determinism)
- **Formal**: `embed(x) = embed(x)`
- **Rationale**: Ensures reproducible behavior

**INV-LLM-M2: Similarity Symmetry**
- **Statement**: Similarity measure is symmetric
- **Formal**: `sim(v1, v2) = sim(v2, v1)`
- **Rationale**: Mathematical property of cosine similarity

**INV-LLM-M3: Embedding Norm Bounds**
- **Statement**: Normalized embeddings have unit norm
- **Formal**: `∥embed_normalized(x)∥ = 1.0 ± ε` where `ε = 1e-6`
- **Rationale**: Ensures normalized vectors for cosine similarity

---

## 2. NeuroCognitiveEngine

### 2.1 Safety Invariants

**INV-NCE-S1: Response Schema Completeness**
- **Statement**: Every response MUST contain all required schema fields
- **Formal**: `∀response: {response, governance, mlsdm, timing, validation_steps, error, rejected_at} ⊆ keys(response)`
- **Rationale**: Ensures structured, parseable outputs for all consumers

**INV-NCE-S2: Moral Threshold Enforcement**
- **Statement**: Accepted responses MUST meet moral threshold requirements
- **Formal**: `response.accepted ⟹ moral_score(response) ≥ moral_threshold`
- **Rationale**: Core safety guarantee of the system

**INV-NCE-S3: Timing Non-Negativity**
- **Statement**: All timing measurements MUST be non-negative
- **Formal**: `∀key ∈ response.timing: response.timing[key] ≥ 0`
- **Rationale**: Physical constraint - time cannot be negative

**INV-NCE-S4: Rejection Reason Validity**
- **Statement**: If rejected, rejection stage MUST be valid and error MUST be set
- **Formal**: `rejected_at ≠ null ⟹ rejected_at ∈ {pre_moral, pre_grammar, fslgs, mlsdm, post_validation} ∧ error ≠ null`
- **Rationale**: Ensures traceable rejection reasons

### 2.2 Liveness Invariants

**INV-NCE-L1: Response Generation**
- **Statement**: Every valid request MUST receive either an accepted response or a structured rejection
- **Formal**: `valid_request ⟹ ◇(response.accepted ∨ response.rejected_at ≠ null)`
- **Rationale**: No silent failures or hanging requests

**INV-NCE-L2: Timeout Guarantee**
- **Statement**: All operations MUST complete within configured timeout
- **Formal**: `operation_time ≤ llm_timeout + overhead_margin`
- **Rationale**: Prevents indefinite blocking

**INV-NCE-L3: Error Propagation**
- **Statement**: Internal errors MUST be reflected in error field
- **Formal**: `internal_exception ⟹ response.error ≠ null ∧ response.rejected_at ≠ null`
- **Rationale**: Ensures observability of failures

### 2.3 Metamorphic Invariants

**INV-NCE-M1: Neutral Phrase Stability**
- **Statement**: Adding neutral phrases should not drastically change moral score
- **Formal**: `|moral_score(prompt) - moral_score(prompt + " please")| < 0.15`
- **Rationale**: System should be robust to polite language variations

**INV-NCE-M2: Rephrasing Consistency**
- **Statement**: Semantically identical prompts should produce similar rejection patterns
- **Formal**: `semantic_equiv(p1, p2) ⟹ (rejected_at(p1) = null ⟺ rejected_at(p2) = null)`
- **Rationale**: System behavior should depend on meaning, not exact wording

**INV-NCE-M3: Cognitive Load Monotonicity**
- **Statement**: Higher cognitive load should not improve response quality
- **Formal**: `load1 > load2 ⟹ quality(resp1) ≤ quality(resp2)`
- **Rationale**: System performance degrades gracefully under load

---

## 3. MoralFilter

### 3.1 Safety Invariants

**INV-MF-S1: Threshold Bounds**
- **Statement**: Moral threshold MUST remain within configured bounds
- **Formal**: `min_threshold ≤ threshold ≤ max_threshold`
- **Rationale**: Prevents extreme values that would block all/no requests

**INV-MF-S2: Score Range Validity**
- **Statement**: Moral scores MUST be in [0, 1] range
- **Formal**: `0 ≤ moral_value ≤ 1`
- **Rationale**: Mathematical constraint of normalized scores

**INV-MF-S3: Accept Rate Validity**
- **Statement**: Accept rate MUST be a valid probability
- **Formal**: `0 ≤ accept_rate ≤ 1`
- **Rationale**: Percentage constraint

### 3.2 Liveness Invariants

**INV-MF-L1: Evaluation Determinism**
- **Statement**: Same input always produces same evaluation result
- **Formal**: `evaluate(score) = evaluate(score)`
- **Rationale**: Ensures reproducible filtering decisions

**INV-MF-L2: Adaptation Convergence**
- **Statement**: Repeated adaptation calls with same accept_rate converge to steady state
- **Formal**: `∀r: lim_{n→∞} adapt^n(r) = threshold_steady_state(r)`
- **Rationale**: Prevents oscillation or divergence

### 3.3 Metamorphic Invariants

**INV-MF-M1: Monotonic Evaluation**
- **Statement**: Higher moral scores are more likely to pass
- **Formal**: `score1 > score2 ⟹ evaluate(score1) ≥ evaluate(score2)`
- **Rationale**: Filter should consistently favor higher moral values

**INV-MF-M2: Adaptation Stability**
- **Statement**: Single adaptation step changes threshold by at most adapt_rate
- **Formal**: `|threshold_new - threshold_old| ≤ adapt_rate`
- **Rationale**: Prevents sudden threshold jumps

**INV-MF-M3: Bounded Drift Under Attack**
- **Statement**: Even under adversarial input stream, threshold stays within bounds
- **Formal**: `∀attack_sequence: min_threshold ≤ threshold_after_attack ≤ max_threshold`
- **Rationale**: Resilience against adversarial adaptation manipulation

---

## 4. WakeSleepController / CognitiveRhythm

### 4.1 Safety Invariants

**INV-WS-S1: Duration Positivity**
- **Statement**: Wake and sleep durations MUST be positive
- **Formal**: `wake_duration > 0 ∧ sleep_duration > 0`
- **Rationale**: Zero or negative durations would break state machine

**INV-WS-S2: Phase Validity**
- **Statement**: Phase MUST be either "wake" or "sleep"
- **Formal**: `phase ∈ {"wake", "sleep"}`
- **Rationale**: Two-state system constraint

**INV-WS-S3: Counter Non-Negativity**
- **Statement**: Counter MUST never go negative
- **Formal**: `counter ≥ 0`
- **Rationale**: Counter represents remaining time

### 4.2 Liveness Invariants

**INV-WS-L1: Eventual Phase Transition**
- **Statement**: System MUST eventually transition between phases
- **Formal**: `phase(t) = "wake" ⟹ ◇(phase(t') = "sleep")`
- **Rationale**: Prevents stuck in single phase

**INV-WS-L2: Step Progress**
- **Statement**: Each step() call decrements counter or transitions phase
- **Formal**: `step() ⟹ (counter' = counter - 1) ∨ (phase' ≠ phase)`
- **Rationale**: Ensures forward progress

**INV-WS-L3: Active Request Processing**
- **Statement**: During wake phase with active request, system MUST NOT return sleep status
- **Formal**: `is_wake() ∧ has_active_request ⟹ ¬sleep_response()`
- **Rationale**: Wake phase should be responsive

### 4.3 Metamorphic Invariants

**INV-WS-M1: Cycle Periodicity**
- **Statement**: Complete cycle duration equals wake_duration + sleep_duration
- **Formal**: `cycle_duration = wake_duration + sleep_duration`
- **Rationale**: Conservation of time in rhythm cycle

**INV-WS-M2: Phase Alternation**
- **Statement**: Phases strictly alternate
- **Formal**: `phase(t1) = "wake" ∧ phase(t2) = "sleep" ∧ t2 > t1 ⟹ ¬∃t': t1 < t' < t2 ∧ phase(t') = phase(t2)`
- **Rationale**: No phase skipping

---

## 5. PELM / MultiLevelSynapticMemory

### 5.1 Safety Invariants

**INV-MEM-S1: Capacity Enforcement**
- **Statement**: Memory MUST NOT exceed configured capacity
- **Formal**: `|L1| + |L2| + |L3| ≤ total_capacity`
- **Rationale**: Hard memory limit enforcement

**INV-MEM-S2: Vector Dimensionality Consistency**
- **Statement**: All vectors in all levels have same dimension
- **Formal**: `∀v ∈ (L1 ∪ L2 ∪ L3): dim(v) = memory_dim`
- **Rationale**: Enables consistent distance calculations

**INV-MEM-S3: Gating Value Bounds**
- **Statement**: Gating values MUST be in [0, 1] range
- **Formal**: `0 ≤ gating12 ≤ 1 ∧ 0 ≤ gating23 ≤ 1`
- **Rationale**: Gating represents probability/weight

**INV-MEM-S4: Lambda Decay Non-Negativity**
- **Statement**: Decay lambdas MUST be non-negative
- **Formal**: `λ_l1 ≥ 0 ∧ λ_l2 ≥ 0 ∧ λ_l3 ≥ 0`
- **Rationale**: Negative decay would cause growth instead

### 5.2 Liveness Invariants

**INV-MEM-L1: Nearest Neighbor Availability**
- **Statement**: With non-empty memory, query MUST find at least one neighbor
- **Formal**: `|memory| > 0 ⟹ |find_nearest(query, k)| ≥ min(k, |memory|)`
- **Rationale**: Search should succeed when data exists

**INV-MEM-L2: Insertion Progress**
- **Statement**: Insert operation MUST eventually complete (no infinite loops)
- **Formal**: `insert(v) ⟹ ◇(|memory| = |memory_old| + 1 ∨ |memory| = capacity)`
- **Rationale**: Operations must terminate

**INV-MEM-L3: Consolidation Completion**
- **Statement**: Consolidation phase MUST complete in bounded time
- **Formal**: `consolidate() ⟹ ◇(consolidation_complete)`
- **Rationale**: Prevents indefinite blocking

### 5.3 Metamorphic Invariants

**INV-MEM-M1: Distance Non-Increase**
- **Statement**: Adding vectors doesn't increase distance to nearest existing neighbor
- **Formal**: `d1 = min_dist(query) ⟹ insert(v) ⟹ min_dist(query) ≤ d1`
- **Rationale**: More data means closer or equal neighbors

**INV-MEM-M2: Consolidation Monotonicity**
- **Statement**: Consolidation moves vectors down levels (L1→L2→L3), never up
- **Formal**: `∀v: level(v, t_before) ≤ level(v, t_after)` (where L1=1, L2=2, L3=3)
- **Rationale**: Memory hierarchy flows from short-term to long-term

**INV-MEM-M3: Retrieval Relevance Ordering**
- **Statement**: Retrieved neighbors are ordered by decreasing relevance
- **Formal**: `∀i < j: relevance(neighbors[i]) ≥ relevance(neighbors[j])`
- **Rationale**: Most relevant results should appear first

**INV-MEM-M4: Overflow Eviction Policy**
- **Statement**: When capacity reached, evicted vectors have lower relevance than retained
- **Formal**: `capacity_overflow ⟹ ∀v_retained, v_evicted: relevance(v_retained) ≥ relevance(v_evicted)`
- **Rationale**: Keep most important memories

---

## 6. Global Memory Safety (CognitiveController)

### 6.1 Critical Safety Invariant

**INV_GLOBAL_MEM: Global Memory Bound (CORE-04)**
- **Statement**: Total memory usage of the cognitive circuit MUST NOT exceed 1.4 GB
- **Formal**: `∀t: memory_usage_bytes(t) ≤ MAX_MEMORY_BYTES` where `MAX_MEMORY_BYTES = 1.4 × 2³⁰ bytes`
- **Components Covered**:
  - `PELM.memory_usage_bytes()` - Phase-Entangled Lattice Memory arrays
  - `MultiLevelSynapticMemory.memory_usage_bytes()` - L1/L2/L3 synaptic arrays
  - Controller internal buffers (caches, state objects)
- **Rationale**: Hard limit on memory prevents unbounded growth and enables edge deployment

### 6.2 Memory Estimation Requirements

**INV-GMEM-EST: Conservative Memory Estimation**
- **Statement**: Memory estimation MUST be conservative (10-20% overhead)
- **Formal**: `estimated_usage(component) ≥ actual_usage(component)`
- **Rationale**: Better to slightly overestimate than underestimate and breach limit

### 6.3 Emergency Shutdown Behavior

**INV-GMEM-SHUTDOWN: Safe Emergency Transition**
- **Statement**: When memory limit is exceeded, system MUST transition to emergency_shutdown
- **Formal**: `memory_usage_bytes() > MAX_MEMORY_BYTES ⟹ emergency_shutdown = true`
- **Enforcement**: Checked in `CognitiveController.process_event()` after memory-modifying operations

**INV-GMEM-BLOCK: No Further Growth After Shutdown**
- **Statement**: After emergency_shutdown, memory_usage_bytes() MUST NOT increase
- **Formal**: `emergency_shutdown = true ⟹ ∀t' > t: memory_usage_bytes(t') ≤ memory_usage_bytes(t)`
- **Rationale**: New events are rejected, preventing further memory allocation

**INV-GMEM-REASON: Shutdown Reason Logging**
- **Statement**: Emergency shutdown MUST record the cause for diagnostics
- **Formal**: `emergency_shutdown = true ⟹ emergency_reason ∈ {"memory_limit_exceeded", ...}`
- **Rationale**: Enables debugging and post-mortem analysis

### 6.4 Recovery Constraints

**INV-GMEM-RECOVERY: Safe Recovery Conditions**
- **Statement**: Auto-recovery from memory-related shutdown requires memory to be below safety threshold
- **Formal**: `auto_recovery() ⟹ memory_usage_bytes() < MAX_MEMORY_BYTES × safety_ratio`
- **Default**: `safety_ratio = 0.8` (80% of max limit)
- **Rationale**: Prevent immediate re-triggering of shutdown

---

## 7. Testing Strategy

### 7.1 Property-Based Testing with Hypothesis

All invariants are tested using Hypothesis with:
- **Strategies**: Generate random inputs (prompts, vectors, scores, sequences)
- **Shrinking**: Minimize failing examples to simplest counterexample
- **Coverage**: 1000+ examples per property by default
- **Determinism**: Fixed random seed for reproducibility

### 7.2 Test Organization

- `tests/property/test_invariants_neuro_engine.py` - NCE invariants
- `tests/property/test_invariants_memory.py` - Memory system invariants
- `tests/property/test_invariants_moral_filter.py` - Moral filter invariants
- `tests/property/test_global_memory_invariant.py` - Global memory bound tests (CORE-04)
- `tests/property/test_counterexamples_regression.py` - Regression tests

### 7.3 Counterexamples Bank

Failed property tests produce minimal counterexamples stored in:
- `tests/property/counterexamples/moral_filter_counterexamples.json`
- `tests/property/counterexamples/coherence_counterexamples.json`
- `tests/property/counterexamples/memory_counterexamples.json`

These serve as regression tests to ensure fixed bugs don't reappear.

---

## 8. Enforcement

### 8.1 Runtime Assertions

Critical invariants are enforced at runtime with assertions:
```python
assert min_threshold <= threshold <= max_threshold, "INV-MF-S1 violated"
```

### 8.2 CI Integration

Property tests run on every PR via `.github/workflows/property-tests.yml`

Failure of any invariant test blocks merge.

### 8.3 Monitoring

Production systems should monitor invariant violations via metrics:
- `invariant_violation_total{invariant="INV-*"}` - Counter of violations
- Alert on any violation occurrence

---

## 9. Homeostasis & Neuromodulation

### 9.1 Safety Invariants

**INV-HOME-S1: Neuromodulator Bounds**
- **Statement**: Neuromodulator parameters MUST remain within configured ranges.
- **Formal**: `∀p ∈ {exploration, learning_rate, consolidation, strictness}: min_p ≤ p ≤ max_p`
- **Rationale**: Prevents uncontrolled adaptation and keeps modulation inspectable.

**INV-HOME-S2: Governance Dominance**
- **Statement**: Governance inhibition MUST dominate neuromodulator settings.
- **Formal**: `allow_execution=false ⟹ action.type = blocked`
- **Rationale**: Ensures modulators cannot bypass policy gates.

### 9.2 Liveness Invariants

**INV-HOME-L1: Error Accumulator Saturation**
- **Statement**: Prediction error accumulator MUST saturate at a fixed maximum.
- **Formal**: `cumulative_error ≤ max_cumulative_error`
- **Rationale**: Prevents silent error drift over long runtimes.

**INV-HOME-L2: Homeostatic Brake**
- **Statement**: High memory pressure MUST reduce exploration and learning rate.
- **Formal**: `memory_pressure ≥ threshold ⟹ exploration' ≤ exploration ∧ lr' ≤ lr`
- **Rationale**: Stabilizes long-term behavior under resource pressure.

---

## 10. Maintenance

### 10.1 Adding New Invariants

1. Document in this file with clear formal statement
2. Implement property test in appropriate test file
3. Add to CI workflow
4. Update `VALIDATION_SUMMARY.md` coverage table

### 10.2 Handling Violations

When property test fails:
1. Examine shrunk counterexample
2. Determine if bug in code or invariant statement
3. Fix code or refine invariant
4. Add counterexample to regression bank
5. Re-run full property test suite

---

## 11. References

- **Property-Based Testing**: [Hypothesis documentation](https://hypothesis.readthedocs.io/)
- **Formal Methods**: "Software Foundations" (Pierce et al.)
- **Invariant Design**: "Design by Contract" (Meyer)
- **Temporal Logic**: LTL/CTL operators (◇ = eventually, □ = always)

---

**Status**: ✅ Documented
**Coverage**: 100% of core modules
**Last Updated**: 2025-11-28
**Maintainer**: neuron7x
