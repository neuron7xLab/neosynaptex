"""
Property-based tests for MultiLevelSynapticMemory invariants.

Verifies that multi-level synaptic memory maintains documented invariants:
- Decay monotonicity (older events have less weight over time)
- Level transfer thresholds respected
- Gating values control information flow between levels
- No unbounded growth in any level
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory

# Fixed seed for deterministic property tests
PROPERTY_TEST_SEED = 42

# Default decay rates for testing (from MultiLevelSynapticMemory defaults)
# λ_L1 > λ_L2 > λ_L3 ensures L1 decays fastest (short-term), L3 slowest (long-term)
DEFAULT_LAMBDA_L1 = 0.50  # Fastest decay (short-term memory)
DEFAULT_LAMBDA_L2 = 0.10  # Medium decay (working memory)
DEFAULT_LAMBDA_L3 = 0.01  # Slowest decay (long-term memory)

# Tolerance for decay rate comparisons - accounts for floating point precision
# and transfer effects between levels during decay
DECAY_RATE_TOLERANCE = 0.15


@settings(max_examples=30, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=50), num_updates=st.integers(min_value=1, max_value=20)
)
def test_multilevel_decay_monotonicity(dim, num_updates):
    """
    Property: Decay reduces level norms monotonically without new input.
    After stopping updates, each level's norm should decrease or stay zero.
    """
    np.random.seed(PROPERTY_TEST_SEED)
    memory = MultiLevelSynapticMemory(dimension=dim)

    # Add some events to populate levels
    for _ in range(num_updates):
        vec = np.random.randn(dim).astype(np.float32)
        memory.update(vec)

    # Get state after updates
    L1_before, L2_before, L3_before = memory.get_state()
    norm_L1_before = np.linalg.norm(L1_before)
    norm_L2_before = np.linalg.norm(L2_before)
    norm_L3_before = np.linalg.norm(L3_before)

    # Apply decay without new input (zero vector)
    zero_vec = np.zeros(dim, dtype=np.float32)
    memory.update(zero_vec)

    # Get state after decay
    L1_after, L2_after, L3_after = memory.get_state()
    norm_L1_after = np.linalg.norm(L1_after)
    norm_L2_after = np.linalg.norm(L2_after)
    norm_L3_after = np.linalg.norm(L3_after)

    # Decay should reduce or maintain norms (within floating point tolerance)
    assert (
        norm_L1_after <= norm_L1_before + 1e-6
    ), f"L1 norm increased: {norm_L1_before} -> {norm_L1_after}"
    assert (
        norm_L2_after <= norm_L2_before + 1e-6
    ), f"L2 norm increased: {norm_L2_before} -> {norm_L2_after}"
    assert (
        norm_L3_after <= norm_L3_before + 1e-6
    ), f"L3 norm increased: {norm_L3_before} -> {norm_L3_after}"


@settings(max_examples=30, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=50),
    lambda_l1=st.floats(min_value=0.1, max_value=0.9, allow_nan=False),
    lambda_l2=st.floats(min_value=0.01, max_value=0.5, allow_nan=False),
    lambda_l3=st.floats(min_value=0.001, max_value=0.1, allow_nan=False),
)
def test_multilevel_lambda_decay_rates(dim, lambda_l1, lambda_l2, lambda_l3):
    """
    Property: Higher lambda values cause faster decay.
    L1 (fastest) > L2 (medium) > L3 (slowest) when lambda_l1 > lambda_l2 > lambda_l3.
    """
    np.random.seed(PROPERTY_TEST_SEED)

    # Ensure lambda ordering for this test
    if not (lambda_l1 > lambda_l2 > lambda_l3):
        return  # Skip this example

    memory = MultiLevelSynapticMemory(
        dimension=dim, lambda_l1=lambda_l1, lambda_l2=lambda_l2, lambda_l3=lambda_l3
    )

    # Add a large event to all levels (via threshold transfers)
    large_vec = np.ones(dim, dtype=np.float32) * 5.0
    for _ in range(10):
        memory.update(large_vec)

    L1_before, L2_before, L3_before = memory.get_state()

    # Apply multiple decay cycles with zero input
    zero_vec = np.zeros(dim, dtype=np.float32)
    for _ in range(5):
        memory.update(zero_vec)

    L1_after, L2_after, L3_after = memory.get_state()

    # Calculate decay ratios
    decay_L1 = np.linalg.norm(L1_after) / (np.linalg.norm(L1_before) + 1e-9)
    decay_L2 = np.linalg.norm(L2_after) / (np.linalg.norm(L2_before) + 1e-9)
    decay_L3 = np.linalg.norm(L3_after) / (np.linalg.norm(L3_before) + 1e-9)

    # L1 should decay fastest (smallest ratio), L3 slowest (largest ratio)
    # Allow some tolerance for floating point and transfer effects
    assert decay_L1 <= decay_L2 + 0.1, f"L1 should decay faster than L2: {decay_L1} > {decay_L2}"
    assert decay_L2 <= decay_L3 + 0.1, f"L2 should decay faster than L3: {decay_L2} > {decay_L3}"


@settings(max_examples=30, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=50), num_updates=st.integers(min_value=5, max_value=30)
)
def test_multilevel_no_unbounded_growth(dim, num_updates):
    """
    Property: Memory levels do not grow unboundedly.
    With balanced decay and input, norms should stabilize.
    """
    np.random.seed(PROPERTY_TEST_SEED)
    memory = MultiLevelSynapticMemory(dimension=dim)

    # Track max norms
    max_L1_norm = 0.0
    max_L2_norm = 0.0
    max_L3_norm = 0.0

    for _ in range(num_updates):
        vec = np.random.randn(dim).astype(np.float32)
        memory.update(vec)

        L1, L2, L3 = memory.get_state()
        max_L1_norm = max(max_L1_norm, np.linalg.norm(L1))
        max_L2_norm = max(max_L2_norm, np.linalg.norm(L2))
        max_L3_norm = max(max_L3_norm, np.linalg.norm(L3))

    # Norms should be bounded (not infinite or extremely large)
    assert max_L1_norm < 1000 * np.sqrt(dim), f"L1 norm unbounded: {max_L1_norm}"
    assert max_L2_norm < 1000 * np.sqrt(dim), f"L2 norm unbounded: {max_L2_norm}"
    assert max_L3_norm < 1000 * np.sqrt(dim), f"L3 norm unbounded: {max_L3_norm}"


def test_multilevel_gating_bounds():
    """
    Property: Gating values are stored within bounds [0, 1].
    """
    np.random.seed(PROPERTY_TEST_SEED)
    dim = 10

    # Test various gating values
    memory = MultiLevelSynapticMemory(dimension=dim, gating12=0.45, gating23=0.30)

    # Gating values should be within bounds
    assert 0.0 <= memory.gating12 <= 1.0, f"gating12 out of bounds: {memory.gating12}"
    assert 0.0 <= memory.gating23 <= 1.0, f"gating23 out of bounds: {memory.gating23}"

    # Test edge cases
    memory_min = MultiLevelSynapticMemory(dimension=dim, gating12=0.0, gating23=0.0)
    assert memory_min.gating12 == 0.0
    assert memory_min.gating23 == 0.0

    memory_max = MultiLevelSynapticMemory(dimension=dim, gating12=1.0, gating23=1.0)
    assert memory_max.gating12 == 1.0
    assert memory_max.gating23 == 1.0


def test_multilevel_reset_clears_all_levels():
    """Test that reset_all clears all three levels."""
    memory = MultiLevelSynapticMemory(dimension=10)

    # Add events
    for _ in range(5):
        vec = np.random.randn(10).astype(np.float32)
        memory.update(vec)

    # Verify levels are non-zero
    L1, L2, L3 = memory.get_state()
    assert np.linalg.norm(L1) > 0 or np.linalg.norm(L2) > 0 or np.linalg.norm(L3) > 0

    # Reset
    memory.reset_all()

    # Verify all levels are zero
    L1, L2, L3 = memory.get_state()
    assert np.allclose(L1, 0.0), "L1 not cleared"
    assert np.allclose(L2, 0.0), "L2 not cleared"
    assert np.allclose(L3, 0.0), "L3 not cleared"


def test_multilevel_dimension_consistency():
    """Test that all levels maintain correct dimension."""
    dim = 20
    memory = MultiLevelSynapticMemory(dimension=dim)

    # Add events
    for _ in range(5):
        vec = np.random.randn(dim).astype(np.float32)
        memory.update(vec)

    L1, L2, L3 = memory.get_state()

    assert L1.shape[0] == dim, f"L1 dimension mismatch: {L1.shape[0]} != {dim}"
    assert L2.shape[0] == dim, f"L2 dimension mismatch: {L2.shape[0]} != {dim}"
    assert L3.shape[0] == dim, f"L3 dimension mismatch: {L3.shape[0]} != {dim}"


def test_multilevel_invalid_inputs():
    """Test that invalid inputs raise appropriate errors."""
    # Invalid dimension
    with pytest.raises(ValueError, match="dimension must be positive"):
        MultiLevelSynapticMemory(dimension=0)

    # Invalid lambda values
    with pytest.raises(ValueError, match="lambda_l1"):
        MultiLevelSynapticMemory(dimension=10, lambda_l1=0.0)

    with pytest.raises(ValueError, match="lambda_l1"):
        MultiLevelSynapticMemory(dimension=10, lambda_l1=1.5)

    # Invalid gating values
    with pytest.raises(ValueError, match="gating12"):
        MultiLevelSynapticMemory(dimension=10, gating12=-0.1)

    with pytest.raises(ValueError, match="gating12"):
        MultiLevelSynapticMemory(dimension=10, gating12=1.5)


def test_multilevel_to_dict_serialization():
    """Test that to_dict returns correct structure."""
    memory = MultiLevelSynapticMemory(dimension=10, lambda_l1=0.5, lambda_l2=0.1, lambda_l3=0.01)

    # Add an event
    vec = np.ones(10, dtype=np.float32)
    memory.update(vec)

    state_dict = memory.to_dict()

    # Check required keys
    assert "dimension" in state_dict
    assert "lambda_l1" in state_dict
    assert "lambda_l2" in state_dict
    assert "lambda_l3" in state_dict
    assert "theta_l1" in state_dict
    assert "theta_l2" in state_dict
    assert "gating12" in state_dict
    assert "gating23" in state_dict
    assert "state_L1" in state_dict
    assert "state_L2" in state_dict
    assert "state_L3" in state_dict

    # Check values
    assert state_dict["dimension"] == 10
    assert state_dict["lambda_l1"] == 0.5
    assert len(state_dict["state_L1"]) == 10


# ============================================================================
# Additional Property Tests for Phase 3 Tech-Debt
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=50), num_updates=st.integers(min_value=20, max_value=100)
)
def test_multilevel_l1_decays_faster_than_l2_l3(dim, num_updates):
    """
    INV-ML-4 (from docs): L1 decays faster than L2, L2 decays faster than L3.

    With default lambdas: λ_L1=0.50 > λ_L2=0.10 > λ_L3=0.01
    After stopping updates, L1 norm should decrease faster than L2 and L3.
    """
    np.random.seed(PROPERTY_TEST_SEED)

    # Use default lambdas which enforce λ_L1 > λ_L2 > λ_L3
    memory = MultiLevelSynapticMemory(
        dimension=dim,
        lambda_l1=DEFAULT_LAMBDA_L1,
        lambda_l2=DEFAULT_LAMBDA_L2,
        lambda_l3=DEFAULT_LAMBDA_L3,
    )

    # Build up state with updates
    for _ in range(num_updates):
        vec = np.random.randn(dim).astype(np.float32)
        memory.update(vec)

    # Record norms before decay
    L1_before, L2_before, L3_before = memory.get_state()
    norm_L1_before = np.linalg.norm(L1_before)
    norm_L2_before = np.linalg.norm(L2_before)
    norm_L3_before = np.linalg.norm(L3_before)

    # Skip if levels are too small to measure decay meaningfully
    if norm_L1_before < 1e-6 and norm_L2_before < 1e-6:
        return  # Skip this example - insufficient signal to test

    # Apply decay with zero vectors (no new input, only decay)
    zero_vec = np.zeros(dim, dtype=np.float32)
    for _ in range(10):  # Multiple decay cycles
        memory.update(zero_vec)

    # Record norms after decay
    L1_after, L2_after, L3_after = memory.get_state()
    norm_L1_after = np.linalg.norm(L1_after)
    norm_L2_after = np.linalg.norm(L2_after)
    norm_L3_after = np.linalg.norm(L3_after)

    # Calculate retention ratios (higher ratio = less decay)
    # Add small epsilon to avoid division by zero
    eps = 1e-9
    retention_L1 = norm_L1_after / (norm_L1_before + eps) if norm_L1_before > eps else 1.0
    retention_L2 = norm_L2_after / (norm_L2_before + eps) if norm_L2_before > eps else 1.0
    retention_L3 = norm_L3_after / (norm_L3_before + eps) if norm_L3_before > eps else 1.0

    # L1 should have lower retention (decayed more) than L2 and L3
    # Only assert if we had meaningful initial content
    if norm_L1_before > 1e-3:
        assert (
            retention_L1 <= retention_L2 + DECAY_RATE_TOLERANCE
        ), f"L1 retention ({retention_L1:.4f}) should be <= L2 retention ({retention_L2:.4f})"

    if norm_L2_before > 1e-3:
        assert (
            retention_L2 <= retention_L3 + DECAY_RATE_TOLERANCE
        ), f"L2 retention ({retention_L2:.4f}) should be <= L3 retention ({retention_L3:.4f})"


@settings(max_examples=30, deadline=None)
@given(
    dim=st.integers(min_value=5, max_value=50), num_updates=st.integers(min_value=50, max_value=200)
)
def test_multilevel_memory_no_leak_under_load(dim, num_updates):
    """
    INV-ML-3 (from docs): No unbounded growth / memory leak.

    Under sustained random load, memory norms should stabilize and not
    grow without bound.
    """
    np.random.seed(PROPERTY_TEST_SEED)
    memory = MultiLevelSynapticMemory(dimension=dim)

    # Track max norms over time
    max_total_norm = 0.0
    norms_history = []

    for i in range(num_updates):
        vec = np.random.randn(dim).astype(np.float32)
        memory.update(vec)

        L1, L2, L3 = memory.get_state()
        total_norm = np.linalg.norm(L1) + np.linalg.norm(L2) + np.linalg.norm(L3)
        max_total_norm = max(max_total_norm, total_norm)
        norms_history.append(total_norm)

    # Verify bounded growth - should not grow exponentially
    # With decay parameters, memory should reach steady state
    theoretical_max = 1000 * np.sqrt(dim)  # Conservative upper bound

    assert (
        max_total_norm < theoretical_max
    ), f"Memory norm grew unboundedly: max={max_total_norm}, bound={theoretical_max}"

    # Verify stabilization: recent norms should be similar (steady state)
    if len(norms_history) >= 20:
        recent_norms = norms_history[-20:]
        std_recent = np.std(recent_norms)
        mean_recent = np.mean(recent_norms)

        # Coefficient of variation should be reasonable (not wildly oscillating)
        if mean_recent > 1e-3:
            cv = std_recent / mean_recent
            assert (
                cv < 1.0
            ), f"Memory norms not stable: CV={cv:.3f} (std={std_recent:.3f}, mean={mean_recent:.3f})"


@settings(max_examples=30, deadline=None)
@given(dim=st.integers(min_value=5, max_value=50))
def test_multilevel_level_isolation_under_threshold(dim):
    """
    Test that small inputs stay in L1 and don't transfer to L2/L3.

    When input signals are below theta_l1 threshold, they should
    decay in L1 without transferring to deeper levels.
    """
    np.random.seed(PROPERTY_TEST_SEED)

    # Use high thresholds to prevent transfers
    memory = MultiLevelSynapticMemory(
        dimension=dim,
        theta_l1=100.0,  # Very high - L1 won't exceed this
        theta_l2=100.0,  # Very high - L2 won't exceed this
        gating12=0.5,
        gating23=0.3,
    )

    # Add small vectors that won't exceed thresholds
    for _ in range(20):
        vec = np.random.randn(dim).astype(np.float32) * 0.1  # Small magnitude
        memory.update(vec)

    L1, L2, L3 = memory.get_state()

    # L1 should have content (receives input)
    # L2 and L3 should have minimal content (threshold blocks transfers)
    norm_L2 = np.linalg.norm(L2)
    norm_L3 = np.linalg.norm(L3)

    # With very high thresholds, transfers should be minimal
    # (Some leakage is possible due to implementation details)
    assert norm_L2 < 1.0, f"L2 should be near-empty with high threshold, got norm={norm_L2}"
    assert norm_L3 < 1.0, f"L3 should be near-empty with high threshold, got norm={norm_L3}"


@settings(max_examples=30, deadline=None)
@given(dim=st.integers(min_value=5, max_value=50))
def test_multilevel_full_transfer_cascade(dim):
    """
    Test that large inputs cascade through all levels.

    When inputs significantly exceed thresholds, they should
    transfer from L1 → L2 → L3.
    """
    np.random.seed(PROPERTY_TEST_SEED)

    # Use low thresholds to encourage transfers
    memory = MultiLevelSynapticMemory(
        dimension=dim,
        theta_l1=0.1,  # Low - easy to exceed
        theta_l2=0.1,  # Low - easy to exceed
        gating12=0.9,  # High transfer rate
        gating23=0.9,  # High transfer rate
    )

    # Add large vectors to trigger transfers
    for _ in range(30):
        vec = np.random.randn(dim).astype(np.float32) * 10.0  # Large magnitude
        memory.update(vec)

    L1, L2, L3 = memory.get_state()

    # All levels should have content due to cascade
    norm_L2 = np.linalg.norm(L2)
    norm_L3 = np.linalg.norm(L3)

    assert norm_L2 > 0.01, f"L2 should have content from transfers, got norm={norm_L2}"
    assert norm_L3 > 0.01, f"L3 should have content from cascade, got norm={norm_L3}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
