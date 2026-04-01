"""
Property-based tests for PELM phase-aware behavior.

Verifies that phase-entangled retrieval works as specified:
- Vectors stored during wake phase should be retrievable during wake
- Vectors stored during sleep phase should be retrievable during sleep
- Phase tolerance controls cross-phase retrieval
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

# Phase constants matching those used in cognitive_controller
# These values (0.1 for wake, 0.9 for sleep) create maximum separation
# in phase space, ensuring clear distinction between wake/sleep retrieval
# patterns. The 0.8 phase distance allows tight tolerance (0.15) to
# effectively isolate wake from sleep memories.
WAKE_PHASE = 0.1
SLEEP_PHASE = 0.9


def test_pelm_phase_isolation_wake_only():
    """Test that wake-phase vectors are retrievable during wake but not sleep (strict)."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store vectors during wake phase
    wake_vectors = []
    for i in range(5):
        vec = np.random.randn(10).astype(np.float32)
        wake_vectors.append(vec)
        pelm.entangle(vec.tolist(), phase=WAKE_PHASE)

    # Query during wake phase with tight tolerance
    query = wake_vectors[0]  # Use stored vector as query
    results_wake = pelm.retrieve(
        query.tolist(),
        current_phase=WAKE_PHASE,
        phase_tolerance=0.05,  # Tight tolerance
        top_k=5,
    )

    # Should find the vectors
    assert len(results_wake) > 0, "Should find wake-phase vectors during wake query"

    # Query during sleep phase with same tight tolerance
    results_sleep = pelm.retrieve(
        query.tolist(),
        current_phase=SLEEP_PHASE,
        phase_tolerance=0.05,  # Tight tolerance
        top_k=5,
    )

    # Should NOT find vectors (phase difference ~0.8, tolerance 0.05)
    assert (
        len(results_sleep) == 0
    ), f"Should not find wake vectors during sleep with tight tolerance, found {len(results_sleep)}"


def test_pelm_phase_isolation_sleep_only():
    """Test that sleep-phase vectors are retrievable during sleep but not wake (strict)."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store vectors during sleep phase
    sleep_vectors = []
    for i in range(5):
        vec = np.random.randn(10).astype(np.float32)
        sleep_vectors.append(vec)
        pelm.entangle(vec.tolist(), phase=SLEEP_PHASE)

    # Query during sleep phase with tight tolerance
    query = sleep_vectors[0]
    results_sleep = pelm.retrieve(
        query.tolist(), current_phase=SLEEP_PHASE, phase_tolerance=0.05, top_k=5
    )

    # Should find the vectors
    assert len(results_sleep) > 0, "Should find sleep-phase vectors during sleep query"

    # Query during wake phase with tight tolerance
    results_wake = pelm.retrieve(
        query.tolist(), current_phase=WAKE_PHASE, phase_tolerance=0.05, top_k=5
    )

    # Should NOT find vectors
    assert (
        len(results_wake) == 0
    ), f"Should not find sleep vectors during wake with tight tolerance, found {len(results_wake)}"


def test_pelm_phase_tolerance_controls_retrieval():
    """Test that phase_tolerance parameter controls cross-phase retrieval."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store vector during wake phase
    vec = np.random.randn(10).astype(np.float32)
    pelm.entangle(vec.tolist(), phase=WAKE_PHASE)

    # Query during sleep with TIGHT tolerance - should find nothing
    results_tight = pelm.retrieve(
        vec.tolist(), current_phase=SLEEP_PHASE, phase_tolerance=0.05, top_k=5
    )
    assert len(results_tight) == 0, "Tight tolerance should not retrieve cross-phase"

    # Query during sleep with LOOSE tolerance - should find it
    results_loose = pelm.retrieve(
        vec.tolist(),
        current_phase=SLEEP_PHASE,
        phase_tolerance=1.0,  # Loose tolerance
        top_k=5,
    )
    assert len(results_loose) > 0, "Loose tolerance should retrieve cross-phase"


def test_pelm_phase_mixed_storage():
    """Test retrieval behavior with mixed wake/sleep vectors."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store 5 wake vectors
    wake_vectors = []
    for i in range(5):
        vec = np.random.randn(10).astype(np.float32)
        wake_vectors.append(vec)
        pelm.entangle(vec.tolist(), phase=WAKE_PHASE)

    # Store 5 sleep vectors
    sleep_vectors = []
    for i in range(5):
        vec = np.random.randn(10).astype(np.float32)
        sleep_vectors.append(vec)
        pelm.entangle(vec.tolist(), phase=SLEEP_PHASE)

    # Query wake vector during wake phase with moderate tolerance
    query_wake = wake_vectors[0]
    results_wake = pelm.retrieve(
        query_wake.tolist(),
        current_phase=WAKE_PHASE,
        phase_tolerance=0.15,  # Default tolerance from docs
        top_k=10,
    )

    # Should primarily find wake vectors
    wake_count = sum(1 for r in results_wake if abs(r.phase - WAKE_PHASE) < 0.15)
    assert wake_count > 0, "Should find wake vectors during wake query"

    # Query sleep vector during sleep phase with moderate tolerance
    query_sleep = sleep_vectors[0]
    results_sleep = pelm.retrieve(
        query_sleep.tolist(), current_phase=SLEEP_PHASE, phase_tolerance=0.15, top_k=10
    )

    # Should primarily find sleep vectors
    sleep_count = sum(1 for r in results_sleep if abs(r.phase - SLEEP_PHASE) < 0.15)
    assert sleep_count > 0, "Should find sleep vectors during sleep query"


def test_pelm_phase_values_stored_correctly():
    """Test that phase values are stored and returned correctly."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store with specific phase
    vec = np.random.randn(10).astype(np.float32)
    stored_phase = 0.42
    pelm.entangle(vec.tolist(), phase=stored_phase)

    # Retrieve with loose tolerance
    results = pelm.retrieve(vec.tolist(), current_phase=stored_phase, phase_tolerance=1.0, top_k=1)

    assert len(results) == 1
    # Phase should match what was stored (within floating point precision)
    assert (
        abs(results[0].phase - stored_phase) < 1e-5
    ), f"Phase mismatch: stored {stored_phase}, got {results[0].phase}"


@settings(max_examples=30, deadline=None)
@given(
    num_vectors=st.integers(min_value=5, max_value=20),
    query_phase=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_pelm_property_phase_filtering(num_vectors, query_phase):
    """
    Property test: Phase tolerance strictly filters retrieval results.
    All retrieved vectors must satisfy: |vector_phase - query_phase| <= tolerance
    """
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store vectors with random phases
    phases = np.random.uniform(0.0, 1.0, num_vectors)
    for i in range(num_vectors):
        vec = np.random.randn(10).astype(np.float32)
        pelm.entangle(vec.tolist(), phase=float(phases[i]))

    # Query with specific tolerance
    tolerance = 0.2
    query = np.random.randn(10).astype(np.float32)
    results = pelm.retrieve(
        query.tolist(), current_phase=query_phase, phase_tolerance=tolerance, top_k=num_vectors
    )

    # All results must satisfy phase constraint
    for retrieval in results:
        phase_diff = abs(retrieval.phase - query_phase)
        assert (
            phase_diff <= tolerance
        ), f"Retrieved vector violates phase tolerance: diff={phase_diff} > {tolerance}"


@settings(max_examples=30, deadline=None)
@given(
    wake_count=st.integers(min_value=1, max_value=10),
    sleep_count=st.integers(min_value=1, max_value=10),
)
def test_pelm_property_phase_separation(wake_count, sleep_count):
    """
    Property test: Phase separation prevents cross-phase leakage with tight tolerance.
    """
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store wake vectors
    wake_vectors = []
    for _ in range(wake_count):
        vec = np.random.randn(10).astype(np.float32)
        wake_vectors.append(vec)
        pelm.entangle(vec.tolist(), phase=WAKE_PHASE)

    # Store sleep vectors
    sleep_vectors = []
    for _ in range(sleep_count):
        vec = np.random.randn(10).astype(np.float32)
        sleep_vectors.append(vec)
        pelm.entangle(vec.tolist(), phase=SLEEP_PHASE)

    # Query wake vector during sleep with tight tolerance
    if wake_vectors:
        results = pelm.retrieve(
            wake_vectors[0].tolist(),
            current_phase=SLEEP_PHASE,
            phase_tolerance=0.05,  # Very tight
            top_k=wake_count + sleep_count,
        )

        # Should not retrieve any wake vectors (phase difference ~0.8)
        wake_in_results = sum(1 for r in results if abs(r.phase - WAKE_PHASE) < 0.1)
        assert (
            wake_in_results == 0
        ), f"Found {wake_in_results} wake vectors during sleep query with tight tolerance"


def test_pelm_resonance_with_phase():
    """Test that resonance score is computed correctly for phase-filtered results."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store a known vector
    vec = np.ones(10, dtype=np.float32)
    vec = vec / np.linalg.norm(vec)  # Normalize
    pelm.entangle(vec.tolist(), phase=0.5)

    # Query with same vector (should have high similarity)
    results = pelm.retrieve(vec.tolist(), current_phase=0.5, phase_tolerance=0.1, top_k=1)

    assert len(results) == 1
    # Resonance should be very high (close to 1.0) for self-query
    assert (
        results[0].resonance > 0.95
    ), f"Self-query should have high resonance, got {results[0].resonance}"


def test_pelm_empty_results_outside_phase():
    """Test that queries outside all stored phases return empty results."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    # Store vectors all at phase 0.5
    for _ in range(5):
        vec = np.random.randn(10).astype(np.float32)
        pelm.entangle(vec.tolist(), phase=0.5)

    # Query at phase 0.0 with very tight tolerance
    query = np.random.randn(10).astype(np.float32)
    results = pelm.retrieve(query.tolist(), current_phase=0.0, phase_tolerance=0.01, top_k=5)

    # Should return empty (all vectors at phase 0.5, query at 0.0, tolerance 0.01)
    assert len(results) == 0, "Should return empty when no vectors in phase range"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
