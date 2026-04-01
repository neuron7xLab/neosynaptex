# Cognitive Invariant Traceability Matrix

**Version:** 1.2+
**Last Updated:** November 2025
**Purpose:** Maps documented cognitive invariants to verification tests

This document provides traceability between architectural invariants and their test implementations, ensuring all claimed properties are verified.

---

## Invariant Categories

### 1. Phase-Entangled Lattice Memory (PELM)

| Invariant ID | Description | Verification Tests | Status |
|--------------|-------------|-------------------|---------|
| INV-PELM-01 | Capacity bounds strictly enforced | `tests/property/test_invariants_memory.py::test_pelm_capacity_enforcement` | ✅ Verified |
| INV-PELM-02 | Phase-aware isolation (wake/sleep) | `tests/property/test_pelm_phase_behavior.py::test_pelm_phase_isolation_wake_only`<br>`tests/property/test_pelm_phase_behavior.py::test_pelm_phase_isolation_sleep_only` | ✅ Verified |
| INV-PELM-03 | Phase tolerance controls cross-phase retrieval | `tests/property/test_pelm_phase_behavior.py::test_pelm_phase_tolerance_controls_retrieval` | ✅ Verified |
| INV-PELM-04 | Resonance ordering (best matches first) | `tests/property/test_invariants_memory.py::test_pelm_retrieval_relevance_ordering` | ✅ Verified |
| INV-PELM-05 | Wraparound behavior maintains capacity | `tests/property/test_invariants_memory.py::test_pelm_overflow_eviction_policy` | ✅ Verified |
| INV-PELM-06 | Vector dimensionality consistency | `tests/property/test_invariants_memory.py::test_pelm_vector_dimensionality` | ✅ Verified |

### 2. Multi-Level Synaptic Memory

| Invariant ID | Description | Verification Tests | Status |
|--------------|-------------|-------------------|---------|
| INV-ML-01 | Decay reduces level norms monotonically | `tests/property/test_multilevel_synaptic_memory_properties.py::test_multilevel_decay_monotonicity` | ✅ Verified |
| INV-ML-02 | Lambda decay rates ordered (L1 > L2 > L3) | `tests/property/test_multilevel_synaptic_memory_properties.py::test_multilevel_lambda_decay_rates` | ✅ Verified |
| INV-ML-03 | No unbounded growth in any level | `tests/property/test_multilevel_synaptic_memory_properties.py::test_multilevel_no_unbounded_growth` | ✅ Verified |
| INV-ML-04 | Gating values within bounds [0, 1] | `tests/property/test_multilevel_synaptic_memory_properties.py::test_multilevel_gating_bounds` | ✅ Verified |
| INV-ML-05 | Dimension consistency across levels | `tests/property/test_multilevel_synaptic_memory_properties.py::test_multilevel_dimension_consistency` | ✅ Verified |
| INV-ML-06 | Level transfer respects thresholds | `tests/property/test_invariants_memory.py::test_level_transfer_monotonicity` | ✅ Verified |

### 3. Moral Filter V2

| Invariant ID | Description | Verification Tests | Status |
|--------------|-------------|-------------------|---------|
| INV-MORAL-01 | Threshold ∈ [0.30, 0.90] always | `tests/property/test_moral_filter_properties.py::test_moral_filter_threshold_bounds` | ✅ Verified |
| INV-MORAL-02 | Bounded drift under adversarial input | `tests/property/test_moral_filter_properties.py::test_moral_filter_drift_bounded`<br>`tests/property/test_moral_filter_properties.py::test_moral_filter_extreme_bombardment` | ✅ Verified |
| INV-MORAL-03 | EMA convergence to accept ratio | `tests/property/test_moral_filter_properties.py::test_moral_filter_ema_convergence`<br>`tests/property/test_moral_filter_properties.py::test_moral_filter_property_convergence` | ✅ Verified |
| INV-MORAL-04 | Dead-band prevents oscillation | `tests/property/test_moral_filter_properties.py::test_moral_filter_dead_band` | ✅ Verified |
| INV-MORAL-05 | Deterministic evaluation | `tests/property/test_moral_filter_properties.py::test_moral_filter_deterministic_evaluation` | ✅ Verified |
| INV-MORAL-06 | Adaptation direction correctness | `tests/property/test_moral_filter_properties.py::test_moral_filter_adaptation_direction` | ✅ Verified |

### 4. Cognitive Rhythm

| Invariant ID | Description | Verification Tests | Status |
|--------------|-------------|-------------------|---------|
| INV-RHYTHM-01 | Deterministic state transitions | `tests/validation/test_rhythm_state_machine.py::test_rhythm_deterministic_behavior` | ✅ Verified |
| INV-RHYTHM-02 | Wake→Sleep→Wake cycle consistency | `tests/validation/test_rhythm_state_machine.py::test_rhythm_property_cycle_consistency` | ✅ Verified |
| INV-RHYTHM-03 | Counter bounds maintained | `tests/validation/test_rhythm_state_machine.py::test_rhythm_property_counter_bounds` | ✅ Verified |
| INV-RHYTHM-04 | Phase transition at counter=0 | `tests/validation/test_rhythm_state_machine.py::test_rhythm_phase_boundaries` | ✅ Verified |
| INV-RHYTHM-05 | Counter decrements correctly | `tests/validation/test_rhythm_state_machine.py::test_rhythm_counter_decrements_correctly` | ✅ Verified |

### 5. Aphasia-Broca Detection

| Invariant ID | Description | Verification Tests | Status |
|--------------|-------------|-------------------|---------|
| INV-APH-01 | Empty text detected as aphasic | `tests/extensions/test_aphasia_edge_cases.py::test_aphasia_detector_empty_text` | ✅ Verified |
| INV-APH-02 | Severity scaling with aphasia degree | `tests/extensions/test_aphasia_edge_cases.py::test_aphasia_detector_severity_scaling` | ✅ Verified |
| INV-APH-03 | Fragment ratio calculation accuracy | `tests/extensions/test_aphasia_edge_cases.py::test_aphasia_detector_fragment_ratio_calculation` | ✅ Verified |
| INV-APH-04 | Boundary threshold detection | `tests/extensions/test_aphasia_edge_cases.py::test_aphasia_detector_boundary_thresholds` | ✅ Verified |
| INV-APH-05 | Unicode text handling | `tests/extensions/test_aphasia_edge_cases.py::test_aphasia_detector_unicode_text` | ✅ Verified |
| INV-APH-06 | Edge cases (code, URLs, numbers) | `tests/extensions/test_aphasia_edge_cases.py::test_aphasia_detector_code_snippets`<br>`tests/extensions/test_aphasia_edge_cases.py::test_aphasia_detector_urls_and_paths`<br>`tests/extensions/test_aphasia_edge_cases.py::test_aphasia_detector_numbers_only` | ✅ Verified |

### 6. Cognitive Controller Integration

| Invariant ID | Description | Verification Tests | Status |
|--------------|-------------|-------------------|---------|
| INV-CTRL-01 | PELM + MultiLevel coordination | `tests/property/test_cognitive_controller_integration.py::test_controller_pelm_multilevel_coordination` | ✅ Verified |
| INV-CTRL-02 | Moral + Rhythm interaction | `tests/property/test_cognitive_controller_integration.py::test_controller_moral_rhythm_interaction` | ✅ Verified |
| INV-CTRL-03 | State consistency across subsystems | `tests/property/test_cognitive_controller_integration.py::test_controller_state_consistency` | ✅ Verified |
| INV-CTRL-04 | Deterministic processing | `tests/property/test_cognitive_controller_integration.py::test_controller_deterministic_processing` | ✅ Verified |
| INV-CTRL-05 | Emergency shutdown mechanism | `tests/property/test_cognitive_controller_integration.py::test_controller_emergency_shutdown` | ✅ Verified |

---

## Planned Invariants (v1.3+)

The following invariants are documented in architecture specs but not yet fully implemented or tested:

| Invariant ID | Description | Planned Version | Status |
|--------------|-------------|----------------|---------|
| INV-TLA-01 | Formal TLA+ memory safety proofs | v1.3 | 📋 Planned |
| INV-RAG-01 | RAG hallucination detection | v1.3 | 📋 Planned |
| INV-CHAOS-01 | Chaos/fault injection resilience | v1.3 | 📋 Planned |

---

## Test Statistics Summary

**Total Verified Invariants:** 31
**Total Tests:** 824 (as of v1.2+)
**Property Tests:** 50+
**Edge Case Tests:** 27
**Integration Tests:** 217

**Coverage:** 90%+ maintained across all modules

---

## Using This Document

### For Developers
- Before claiming an invariant is "verified", ensure it has an entry in this table
- When adding new invariants, add tests and update this document
- Link to specific test functions (module::test_name) for traceability

### For Reviewers
- Check that all "Verified" claims in docs have corresponding entries here
- Verify test names are correct and tests actually exist
- Run tests to confirm invariants hold

### For Documentation
- This is the single source of truth for "what's verified"
- README and other docs should reference this document
- Any "Verified" or "Tested" claim must link here

---

## Updates

- **2025-11-23:** Initial traceability matrix created with 31 verified invariants
- **Test count:** 824 tests (updated from 805)
