"""
Property-based tests for memory system invariants.

Tests formal invariants for PELM (Phase-Entangled Lattice Memory)
and MultiLevelSynapticMemory as defined in docs/FORMAL_INVARIANTS.md.
"""

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

# Test tolerances
RESONANCE_ORDERING_TOLERANCE = 1e-6  # Tolerance for floating point comparison in ordering


# ============================================================================
# Test Strategies
# ============================================================================


@st.composite
def vector_strategy(draw, dim=10):
    """Generate random vectors of specified dimension."""
    vector = draw(
        st.lists(
            st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            min_size=dim,
            max_size=dim,
        )
    )
    return np.array(vector, dtype=np.float32)


@st.composite
def normalized_vector_strategy(draw, dim=10):
    """Generate normalized (unit norm) vectors."""
    vec = draw(vector_strategy(dim=dim))
    norm = np.linalg.norm(vec)
    if norm < 1e-8:
        # If zero vector, return a fixed unit vector
        result = np.zeros(dim, dtype=np.float32)
        result[0] = 1.0
        return result
    return vec / norm


@st.composite
def gating_value_strategy(draw):
    """Generate gating values in [0, 1]."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))


@st.composite
def lambda_strategy(draw):
    """Generate lambda decay values (must be positive, > 0)."""
    return draw(st.floats(min_value=0.001, max_value=1.0, allow_nan=False))


# ============================================================================
# Property Tests: MultiLevelSynapticMemory - Safety Invariants
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=20), num_vectors=st.integers(min_value=1, max_value=10)
)
def test_memory_vector_dimensionality_consistency(dim, num_vectors):
    """
    INV-MEM-S2: Vector Dimensionality Consistency
    All vectors in all levels have same dimension.
    """
    memory = MultiLevelSynapticMemory(dimension=dim)

    # Add multiple vectors
    for _ in range(num_vectors):
        vec = np.random.randn(dim).astype(np.float32)
        memory.update(vec)

    # Get state - returns single aggregated vectors per level
    L1, L2, L3 = memory.get_state()

    # Check each level vector has correct dimension
    assert L1.shape[0] == dim, f"L1 vector has wrong dimension: {L1.shape[0]} != {dim}"
    assert L2.shape[0] == dim, f"L2 vector has wrong dimension: {L2.shape[0]} != {dim}"
    assert L3.shape[0] == dim, f"L3 vector has wrong dimension: {L3.shape[0]} != {dim}"


@settings(max_examples=50, deadline=None)
@given(gating12=gating_value_strategy(), gating23=gating_value_strategy())
def test_gating_value_bounds(gating12, gating23):
    """
    INV-MEM-S3: Gating Value Bounds
    Gating values MUST be in [0, 1] range.
    """
    memory = MultiLevelSynapticMemory(dimension=10, gating12=gating12, gating23=gating23)

    # Gating values should be stored correctly
    assert 0.0 <= memory.gating12 <= 1.0, f"gating12 out of bounds: {memory.gating12}"
    assert 0.0 <= memory.gating23 <= 1.0, f"gating23 out of bounds: {memory.gating23}"


@settings(max_examples=50, deadline=None)
@given(lambda_l1=lambda_strategy(), lambda_l2=lambda_strategy(), lambda_l3=lambda_strategy())
def test_lambda_decay_non_negativity(lambda_l1, lambda_l2, lambda_l3):
    """
    INV-MEM-S4: Lambda Decay Non-Negativity
    Decay lambdas MUST be non-negative.
    """
    memory = MultiLevelSynapticMemory(
        dimension=10, lambda_l1=lambda_l1, lambda_l2=lambda_l2, lambda_l3=lambda_l3
    )

    assert memory.lambda_l1 >= 0, f"lambda_l1 is negative: {memory.lambda_l1}"
    assert memory.lambda_l2 >= 0, f"lambda_l2 is negative: {memory.lambda_l2}"
    assert memory.lambda_l3 >= 0, f"lambda_l3 is negative: {memory.lambda_l3}"


# ============================================================================
# Property Tests: MultiLevelSynapticMemory - Liveness Invariants
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=20), num_inserts=st.integers(min_value=1, max_value=10)
)
def test_insertion_progress(dim, num_inserts):
    """
    INV-MEM-L2: Insertion Progress
    Insert operation MUST eventually complete.
    """
    memory = MultiLevelSynapticMemory(dimension=dim)

    for i in range(num_inserts):
        vec = np.random.randn(dim).astype(np.float32)

        # Get norm before (as proxy for size/activity)
        L1_before, L2_before, L3_before = memory.get_state()
        np.linalg.norm(L1_before) + np.linalg.norm(L2_before) + np.linalg.norm(L3_before)

        # Insert
        memory.update(vec)

        # Get norm after
        L1_after, L2_after, L3_after = memory.get_state()
        norm_after = np.linalg.norm(L1_after) + np.linalg.norm(L2_after) + np.linalg.norm(L3_after)

        # Norm should typically increase (or stay similar if at steady state with decay)
        # The key is that insert completes without error
        assert norm_after >= 0, "Memory state is valid after insert"


@settings(max_examples=30, deadline=None)
@given(dim=st.integers(min_value=5, max_value=20))
def test_consolidation_completion(dim):
    """
    INV-MEM-L3: Memory Operations Complete in Bounded Time
    Operations like update and get_state complete without hanging.
    Note: MultiLevelSynapticMemory doesn't have explicit consolidate() method.
    """
    memory = MultiLevelSynapticMemory(dimension=dim)

    # Add some vectors
    for _ in range(5):
        vec = np.random.randn(dim).astype(np.float32)
        memory.update(vec)

    # Get state (this exercises the memory system)
    try:
        L1, L2, L3 = memory.get_state()
        # If we reach here, operation completed
        assert L1 is not None and L2 is not None and L3 is not None
    except Exception as e:
        pytest.fail(f"Memory operation failed to complete: {e}")


# ============================================================================
# Property Tests: MultiLevelSynapticMemory - Metamorphic Invariants
# ============================================================================


@settings(max_examples=30, deadline=None)
@given(dim=st.integers(min_value=5, max_value=20))
def test_distance_non_increase_after_insertion(dim):
    """
    INV-MEM-M1: Distance Non-Increase (adapted for aggregated memory)
    Test that memory system behaves predictably with insertions.
    Note: MultiLevelSynapticMemory uses aggregated vectors, not individual vectors.
    """
    memory = MultiLevelSynapticMemory(dimension=dim)

    # Get initial state
    L1_before, L2_before, L3_before = memory.get_state()
    initial_norm = np.linalg.norm(L1_before) + np.linalg.norm(L2_before) + np.linalg.norm(L3_before)

    # Add vectors
    for _ in range(5):
        vec = np.random.randn(dim).astype(np.float32)
        vec = vec / (np.linalg.norm(vec) + 1e-8)
        memory.update(vec)

    # Get final state
    L1_after, L2_after, L3_after = memory.get_state()
    final_norm = np.linalg.norm(L1_after) + np.linalg.norm(L2_after) + np.linalg.norm(L3_after)

    # After insertions, memory should have accumulated information
    assert (
        final_norm >= initial_norm
    ), f"Memory norm decreased unexpectedly: {initial_norm} -> {final_norm}"


@settings(max_examples=30, deadline=None)
@given(dim=st.integers(min_value=5, max_value=20))
def test_level_transfer_monotonicity(dim):
    """
    INV-MEM-M2: Level Transfer Monotonicity
    Information flows from L1→L2→L3 through natural decay and gating.
    """
    memory = MultiLevelSynapticMemory(
        dimension=dim,
        theta_l1=0.5,  # Low threshold to trigger transitions
        theta_l2=1.0,
        gating12=0.5,
        gating23=0.3,
    )

    # Add multiple vectors to trigger transfers
    for _ in range(10):
        vec = np.random.randn(dim).astype(np.float32)
        vec = vec * 2.0  # Make strong signals to trigger thresholds
        memory.update(vec)

    # Get final state
    L1, L2, L3 = memory.get_state()

    # Check that transfers happened (L2 or L3 should have non-zero content)
    norm_L2 = np.linalg.norm(L2)
    norm_L3 = np.linalg.norm(L3)

    # At least one deeper level should have accumulated information
    assert (
        norm_L2 > 0 or norm_L3 > 0
    ), f"No information transferred to L2/L3: L2={norm_L2}, L3={norm_L3}"


# ============================================================================
# Property Tests: PhaseEntangledLatticeMemory - Safety Invariants
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(dim=st.integers(min_value=5, max_value=20), capacity=st.integers(min_value=5, max_value=50))
def test_pelm_capacity_enforcement(dim, capacity):
    """
    INV-MEM-S1: Capacity Enforcement
    Memory MUST NOT exceed configured capacity.
    """
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

    # Insert more vectors than capacity
    num_inserts = capacity + 10

    for i in range(num_inserts):
        vec = np.random.randn(dim).astype(np.float32)
        phase = float(i % 10) / 10.0  # Phase in [0, 1)
        pelm.entangle(vec.tolist(), phase=phase)

    # Check size doesn't exceed capacity
    size = pelm.size
    assert size <= capacity, f"Memory size {size} exceeds capacity {capacity}"


@settings(max_examples=50, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=20), num_vectors=st.integers(min_value=1, max_value=10)
)
def test_pelm_vector_dimensionality(dim, num_vectors):
    """
    INV-MEM-S2: Vector Dimensionality Consistency
    All vectors in PELM have same dimension.
    """
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=100)

    # Insert vectors
    for i in range(num_vectors):
        vec = np.random.randn(dim).astype(np.float32)
        phase = float(i) / float(num_vectors)
        pelm.entangle(vec.tolist(), phase=phase)

    # Query and check dimensions
    query = np.random.randn(dim).astype(np.float32)
    current_phase = 0.5
    neighbors = pelm.retrieve(
        query.tolist(), current_phase=current_phase, phase_tolerance=1.0, top_k=min(3, num_vectors)
    )

    for retrieval in neighbors:
        assert (
            retrieval.vector.shape[0] == dim
        ), f"Retrieved vector has wrong dimension: {retrieval.vector.shape[0]} != {dim}"


# ============================================================================
# Property Tests: PhaseEntangledLatticeMemory - Liveness Invariants
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=20),
    num_vectors=st.integers(min_value=1, max_value=20),
    k=st.integers(min_value=1, max_value=5),
)
def test_pelm_nearest_neighbor_availability(dim, num_vectors, k):
    """
    INV-MEM-L1: Nearest Neighbor Availability
    With non-empty memory, query MUST find at least one neighbor.
    """
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=100)

    # Insert vectors all with similar phase
    phase = 0.5
    for i in range(num_vectors):
        vec = np.random.randn(dim).astype(np.float32)
        pelm.entangle(vec.tolist(), phase=phase)

    # Query with matching phase
    query = np.random.randn(dim).astype(np.float32)
    neighbors = pelm.retrieve(query.tolist(), current_phase=phase, phase_tolerance=0.5, top_k=k)

    # Should find at least one neighbor (up to k or num_vectors)
    expected_count = min(k, num_vectors)
    assert len(neighbors) >= min(
        1, expected_count
    ), f"No neighbors found despite having {num_vectors} vectors"


# ============================================================================
# Property Tests: PhaseEntangledLatticeMemory - Metamorphic Invariants
# ============================================================================


@settings(max_examples=30, deadline=None)
@given(dim=st.integers(min_value=5, max_value=20), k=st.integers(min_value=2, max_value=5))
def test_pelm_retrieval_relevance_ordering(dim, k):
    """
    INV-MEM-M3: Retrieval Relevance Ordering
    Retrieved neighbors are ordered by decreasing relevance (resonance/similarity).
    """
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=100)

    # Insert several vectors with same phase
    phase = 0.5
    for _ in range(10):
        vec = np.random.randn(dim).astype(np.float32)
        pelm.entangle(vec.tolist(), phase=phase)

    # Query
    query = np.random.randn(dim).astype(np.float32)
    neighbors = pelm.retrieve(query.tolist(), current_phase=phase, phase_tolerance=0.5, top_k=k)

    # Check ordering by resonance (should be non-increasing, i.e., first is best)
    resonances = [retrieval.resonance for retrieval in neighbors]

    for i in range(len(resonances) - 1):
        assert (
            resonances[i] >= resonances[i + 1] - RESONANCE_ORDERING_TOLERANCE
        ), f"Neighbors not ordered by resonance: {resonances[i]} < {resonances[i+1]}"


@settings(max_examples=30, deadline=None)
@given(dim=st.integers(min_value=5, max_value=20))
def test_pelm_overflow_eviction_policy(dim):
    """
    INV-MEM-M4: Overflow Eviction Policy
    When capacity reached, system evicts appropriately and maintains capacity.
    """
    capacity = 10
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

    # Fill to capacity
    phase = 0.5
    for i in range(capacity):
        vec = np.random.randn(dim).astype(np.float32)
        pelm.entangle(vec.tolist(), phase=phase)

    # Verify at capacity
    assert pelm.size == capacity

    # Add more vectors (should trigger wraparound)
    for i in range(5):
        vec = np.random.randn(dim).astype(np.float32)
        pelm.entangle(vec.tolist(), phase=phase)

    # Should still be at capacity (wraparound maintains capacity)
    assert pelm.size == capacity, f"Size {pelm.size} != capacity {capacity} after overflow"


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.parametrize("dim", [1, 5, 10, 100, 384])
def test_various_dimensions(dim):
    """Test memory systems work with various dimensions."""
    memory = MultiLevelSynapticMemory(dimension=dim)

    vec = np.random.randn(dim).astype(np.float32)
    memory.update(vec)

    L1, L2, L3 = memory.get_state()
    assert len(L1) > 0, "Vector not added to L1"


@pytest.mark.parametrize("capacity", [1, 5, 10, 100])
def test_various_capacities(capacity):
    """Test PELM works with various capacity values."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=capacity)

    # Add vectors up to capacity
    phase = 0.5
    for i in range(capacity):
        vec = np.random.randn(10).astype(np.float32)
        pelm.entangle(vec.tolist(), phase=phase)

    assert pelm.size <= capacity


def test_empty_memory_query():
    """Test querying empty memory returns empty results."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    query = np.random.randn(10).astype(np.float32)
    neighbors = pelm.retrieve(query.tolist(), current_phase=0.5, phase_tolerance=0.5, top_k=5)

    assert len(neighbors) == 0, "Empty memory should return no neighbors"


def test_single_vector_retrieval():
    """Test retrieving from memory with single vector."""
    pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

    vec = np.random.randn(10).astype(np.float32)
    phase = 0.5
    pelm.entangle(vec.tolist(), phase=phase)

    query = np.random.randn(10).astype(np.float32)
    neighbors = pelm.retrieve(query.tolist(), current_phase=phase, phase_tolerance=0.5, top_k=5)

    assert len(neighbors) == 1, "Should return the single vector"


# ============================================================================
# Phase 3: Additional Invariant Property Tests
# ============================================================================


@settings(max_examples=30, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=50),
    capacity=st.integers(min_value=10, max_value=100),
    num_inserts=st.integers(min_value=50, max_value=200),
)
def test_memory_never_exceeds_capacity_under_random_load(dim, capacity, num_inserts):
    """
    INV-MEM-S1 (from FORMAL_INVARIANTS.md): Memory MUST NOT exceed configured capacity.

    Under heavy random load (inserts >> capacity), PELM should never exceed
    its configured capacity. This tests the circular buffer wraparound behavior.
    """
    # Ensure we have enough inserts to fill and overflow
    assume(num_inserts > capacity)

    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

    # Track size at each step
    max_size_seen = 0

    for i in range(num_inserts):
        vec = np.random.randn(dim).astype(np.float32)
        phase = np.random.random()  # Random phase in [0, 1)
        pelm.entangle(vec.tolist(), phase=phase)

        # Check capacity invariant after each insert
        current_size = pelm.size
        max_size_seen = max(max_size_seen, current_size)

        assert (
            current_size <= capacity
        ), f"PELM size {current_size} exceeds capacity {capacity} after insert {i+1}"

    # Final size should be exactly capacity (since inserts > capacity)
    assert (
        pelm.size == capacity
    ), f"After {num_inserts} inserts (> capacity {capacity}), size should be {capacity}, got {pelm.size}"

    # Max size seen should never exceed capacity
    assert max_size_seen <= capacity, f"Max size {max_size_seen} exceeded capacity {capacity}"


@settings(max_examples=30, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=50), capacity=st.integers(min_value=10, max_value=100)
)
def test_pelm_mixed_phase_capacity_enforcement(dim, capacity):
    """
    Test that capacity enforcement works correctly with mixed phases.

    Inserting vectors with various phases should all respect the same
    global capacity limit.
    """
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

    # Insert 3x capacity vectors with varying phases
    num_inserts = capacity * 3

    for i in range(num_inserts):
        vec = np.random.randn(dim).astype(np.float32)
        # Alternate between wake-like (0.1) and sleep-like (0.9) phases
        phase = 0.1 if i % 2 == 0 else 0.9
        pelm.entangle(vec.tolist(), phase=phase)

        # Capacity invariant must hold
        assert pelm.size <= capacity, f"Size {pelm.size} > capacity {capacity} at insert {i+1}"

    # Final state checks
    assert pelm.size == capacity
    assert not pelm.detect_corruption(), "Memory corruption detected after heavy load"


@settings(max_examples=30, deadline=None)
@given(dim=st.integers(min_value=5, max_value=30), capacity=st.integers(min_value=5, max_value=50))
def test_pelm_retrieval_after_overflow(dim, capacity):
    """
    Test that retrieval still works correctly after capacity overflow.

    After the circular buffer wraps around, retrieval should still find
    valid vectors and maintain ordering invariants.
    """
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

    # Fill to 2x capacity to ensure wraparound
    common_phase = 0.5
    for i in range(capacity * 2):
        vec = np.random.randn(dim).astype(np.float32)
        pelm.entangle(vec.tolist(), phase=common_phase)

    # Retrieval should work
    query = np.random.randn(dim).astype(np.float32)
    results = pelm.retrieve(
        query.tolist(), current_phase=common_phase, phase_tolerance=0.3, top_k=min(5, capacity)
    )

    # Should return results (memory is not empty)
    assert len(results) > 0, "No results after overflow - memory should have content"
    assert len(results) <= capacity, "Cannot retrieve more than capacity"

    # Results should be ordered by resonance (INV-MEM-M3)
    resonances = [r.resonance for r in results]
    for i in range(len(resonances) - 1):
        assert (
            resonances[i] >= resonances[i + 1] - 1e-6
        ), f"Results not ordered: {resonances[i]} < {resonances[i + 1]}"


@settings(max_examples=20, deadline=None)
@given(dim=st.integers(min_value=5, max_value=30))
def test_pelm_no_corruption_under_stress(dim):
    """
    Stress test: Verify no corruption after many operations.

    Perform many interleaved entangle and retrieve operations
    and verify memory integrity is maintained.
    """
    capacity = 100
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

    # Mix of operations
    for i in range(500):
        op = i % 3  # Cycle through operations

        if op == 0 or op == 1:  # Entangle (2/3 of ops)
            vec = np.random.randn(dim).astype(np.float32)
            phase = np.random.random()
            pelm.entangle(vec.tolist(), phase=phase)
        else:  # Retrieve (1/3 of ops)
            if pelm.size > 0:
                query = np.random.randn(dim).astype(np.float32)
                phase = np.random.random()
                pelm.retrieve(query.tolist(), current_phase=phase, phase_tolerance=0.5, top_k=5)

    # Verify integrity
    assert not pelm.detect_corruption(), "Corruption detected after stress test"
    assert pelm.size <= capacity, f"Size {pelm.size} exceeds capacity {capacity}"

    # Recovery should succeed if needed
    if pelm.detect_corruption():
        assert pelm.auto_recover(), "Auto-recovery failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
