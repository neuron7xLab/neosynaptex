"""
Comprehensive tests for memory/multi_level_memory.py.

Tests cover:
- MultiLevelSynapticMemory initialization and validation
- Memory update operations
- State retrieval
- Reset functionality
- Serialization
"""

import numpy as np
import pytest

from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory


class TestMultiLevelSynapticMemoryInit:
    """Tests for MultiLevelSynapticMemory initialization."""

    def test_default_initialization(self):
        """Test initialization with default values."""
        memory = MultiLevelSynapticMemory()
        assert memory.dim == 384
        assert memory.lambda_l1 == 0.50
        assert memory.lambda_l2 == 0.10
        assert memory.lambda_l3 == 0.01
        assert memory.theta_l1 == 1.2
        assert memory.theta_l2 == 2.5
        assert memory.gating12 == 0.45
        assert memory.gating23 == 0.30

    def test_custom_initialization(self):
        """Test initialization with custom values."""
        memory = MultiLevelSynapticMemory(
            dimension=128,
            lambda_l1=0.3,
            lambda_l2=0.2,
            lambda_l3=0.1,
            theta_l1=1.5,
            theta_l2=3.0,
            gating12=0.6,
            gating23=0.4,
        )
        assert memory.dim == 128
        assert memory.lambda_l1 == 0.3
        assert memory.lambda_l2 == 0.2
        assert memory.lambda_l3 == 0.1

    def test_initial_state_is_zero(self):
        """Test that initial state is all zeros."""
        memory = MultiLevelSynapticMemory(dimension=10)
        l1, l2, l3 = memory.get_state()
        assert np.allclose(l1, 0)
        assert np.allclose(l2, 0)
        assert np.allclose(l3, 0)

    def test_invalid_dimension_zero(self):
        """Test that zero dimension raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(dimension=0)
        assert "dimension must be positive" in str(exc_info.value)

    def test_invalid_dimension_negative(self):
        """Test that negative dimension raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(dimension=-10)
        assert "dimension must be positive" in str(exc_info.value)

    def test_invalid_lambda_l1_zero(self):
        """Test that zero lambda_l1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(lambda_l1=0)
        assert "lambda_l1 must be in (0, 1]" in str(exc_info.value)

    def test_invalid_lambda_l1_negative(self):
        """Test that negative lambda_l1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(lambda_l1=-0.1)
        assert "lambda_l1 must be in (0, 1]" in str(exc_info.value)

    def test_invalid_lambda_l1_too_large(self):
        """Test that lambda_l1 > 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(lambda_l1=1.5)
        assert "lambda_l1 must be in (0, 1]" in str(exc_info.value)

    def test_invalid_lambda_l2(self):
        """Test that invalid lambda_l2 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(lambda_l2=0)
        assert "lambda_l2 must be in (0, 1]" in str(exc_info.value)

    def test_invalid_lambda_l3(self):
        """Test that invalid lambda_l3 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(lambda_l3=-0.1)
        assert "lambda_l3 must be in (0, 1]" in str(exc_info.value)

    def test_invalid_theta_l1(self):
        """Test that invalid theta_l1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(theta_l1=0)
        assert "theta_l1 must be positive" in str(exc_info.value)

    def test_invalid_theta_l2(self):
        """Test that invalid theta_l2 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(theta_l2=-1)
        assert "theta_l2 must be positive" in str(exc_info.value)

    def test_invalid_gating12_negative(self):
        """Test that negative gating12 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(gating12=-0.1)
        assert "gating12 must be in [0, 1]" in str(exc_info.value)

    def test_invalid_gating12_too_large(self):
        """Test that gating12 > 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(gating12=1.5)
        assert "gating12 must be in [0, 1]" in str(exc_info.value)

    def test_invalid_gating23(self):
        """Test that invalid gating23 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MultiLevelSynapticMemory(gating23=2.0)
        assert "gating23 must be in [0, 1]" in str(exc_info.value)


class TestUpdate:
    """Tests for update method."""

    def test_update_basic(self):
        """Test basic update operation."""
        memory = MultiLevelSynapticMemory(dimension=3)
        event = np.array([1.0, 2.0, 3.0])
        memory.update(event)

        l1, _, _ = memory.get_state()
        # After update, L1 should have some non-zero values
        assert not np.allclose(l1, 0)

    def test_update_invalid_type(self):
        """Test update with non-numpy array raises ValueError."""
        memory = MultiLevelSynapticMemory(dimension=3)
        with pytest.raises(ValueError) as exc_info:
            memory.update([1.0, 2.0, 3.0])  # type: ignore
        assert "NumPy array" in str(exc_info.value)

    def test_update_invalid_dimension(self):
        """Test update with wrong dimension raises ValueError."""
        memory = MultiLevelSynapticMemory(dimension=3)
        with pytest.raises(ValueError) as exc_info:
            memory.update(np.array([1.0, 2.0]))
        assert "dimension 3" in str(exc_info.value)

    def test_update_decay_applied(self):
        """Test that decay is applied on update."""
        memory = MultiLevelSynapticMemory(dimension=3, lambda_l1=0.5)

        # First update
        event = np.array([10.0, 10.0, 10.0], dtype=np.float32)
        memory.update(event)
        l1_first, _, _ = memory.get_state()

        # Second update with zero event - should show decay
        memory.update(np.zeros(3, dtype=np.float32))
        l1_second, _, _ = memory.get_state()

        # L1 should have decayed (approximately half, but transfer may occur)
        assert np.all(l1_second <= l1_first)

    def test_update_with_float32(self):
        """Test update with float32 array (no conversion needed)."""
        memory = MultiLevelSynapticMemory(dimension=3)
        event = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        memory.update(event)

        l1, _, _ = memory.get_state()
        assert l1.dtype == np.float32

    def test_update_with_float64(self):
        """Test update with float64 array (conversion needed)."""
        memory = MultiLevelSynapticMemory(dimension=3)
        event = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        memory.update(event)

        l1, _, _ = memory.get_state()
        assert l1.dtype == np.float32

    def test_transfer_l1_to_l2(self):
        """Test that transfer from L1 to L2 occurs above threshold."""
        # Set up memory with low threshold for easy transfer
        memory = MultiLevelSynapticMemory(
            dimension=3,
            theta_l1=0.5,  # Low threshold
            gating12=0.5,
            lambda_l1=0.1,
            lambda_l2=0.1,
            lambda_l3=0.1,
        )

        # Add enough to exceed threshold
        event = np.array([5.0, 5.0, 5.0], dtype=np.float32)
        memory.update(event)

        _, l2, _ = memory.get_state()
        # L2 should have received some transfer
        assert np.any(l2 > 0)

    def test_multiple_updates(self):
        """Test multiple sequential updates."""
        memory = MultiLevelSynapticMemory(dimension=3)

        for i in range(10):
            event = np.array([float(i), float(i), float(i)])
            memory.update(event)

        l1, l2, l3 = memory.get_state()
        # After multiple updates, all levels should have some activity
        assert not np.allclose(l1, 0) or not np.allclose(l2, 0) or not np.allclose(l3, 0)


class TestState:
    """Tests for state retrieval methods."""

    def test_state_returns_copies(self):
        """Test that state() returns copies, not references."""
        memory = MultiLevelSynapticMemory(dimension=3)
        memory.update(np.array([1.0, 2.0, 3.0]))

        l1_a, l2_a, l3_a = memory.state()
        l1_b, l2_b, l3_b = memory.state()

        # Modifying returned arrays should not affect internal state
        l1_a[0] = 999.0
        l1_c, _, _ = memory.state()
        assert l1_c[0] != 999.0

    def test_get_state_same_as_state(self):
        """Test that get_state() returns same result as state()."""
        memory = MultiLevelSynapticMemory(dimension=3)
        memory.update(np.array([1.0, 2.0, 3.0]))

        state1 = memory.state()
        state2 = memory.get_state()

        for s1, s2 in zip(state1, state2, strict=True):
            assert np.allclose(s1, s2)


class TestResetAll:
    """Tests for reset_all method."""

    def test_reset_all_clears_state(self):
        """Test that reset_all clears all memory levels."""
        memory = MultiLevelSynapticMemory(dimension=3)

        # Add some events
        for _ in range(5):
            memory.update(np.array([1.0, 2.0, 3.0]))

        # Reset
        memory.reset_all()

        l1, l2, l3 = memory.get_state()
        assert np.allclose(l1, 0)
        assert np.allclose(l2, 0)
        assert np.allclose(l3, 0)


class TestToDict:
    """Tests for to_dict serialization."""

    def test_to_dict_structure(self):
        """Test that to_dict returns correct structure."""
        memory = MultiLevelSynapticMemory(dimension=3)
        result = memory.to_dict()

        assert "dimension" in result
        assert "lambda_l1" in result
        assert "lambda_l2" in result
        assert "lambda_l3" in result
        assert "theta_l1" in result
        assert "theta_l2" in result
        assert "gating12" in result
        assert "gating23" in result
        assert "state_L1" in result
        assert "state_L2" in result
        assert "state_L3" in result

    def test_to_dict_values(self):
        """Test that to_dict returns correct values."""
        memory = MultiLevelSynapticMemory(
            dimension=5,
            lambda_l1=0.4,
            lambda_l2=0.2,
            lambda_l3=0.05,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
        )
        result = memory.to_dict()

        assert result["dimension"] == 5
        assert result["lambda_l1"] == 0.4
        assert result["lambda_l2"] == 0.2
        assert result["lambda_l3"] == 0.05
        assert result["theta_l1"] == 1.0
        assert result["theta_l2"] == 2.0
        assert result["gating12"] == 0.5
        assert result["gating23"] == 0.3

    def test_to_dict_state_as_list(self):
        """Test that state is converted to list."""
        memory = MultiLevelSynapticMemory(dimension=3)
        result = memory.to_dict()

        assert isinstance(result["state_L1"], list)
        assert isinstance(result["state_L2"], list)
        assert isinstance(result["state_L3"], list)
        assert len(result["state_L1"]) == 3


class TestGetDefaultFallback:
    """Test _get_default fallback path when _SYNAPTIC_MEMORY_DEFAULTS is None."""

    def test_get_default_fallback_when_defaults_none(self):
        """Test _get_default fallback path when _SYNAPTIC_MEMORY_DEFAULTS is None."""
        # This tests line 38 in multi_level_memory.py
        from unittest.mock import patch

        from mlsdm.memory import multi_level_memory

        # Mock _SYNAPTIC_MEMORY_DEFAULTS to be None
        with patch.object(multi_level_memory, '_SYNAPTIC_MEMORY_DEFAULTS', None):
            # Call _get_default with a fallback value
            result = multi_level_memory._get_default('lambda_l1', 0.99)

            # Should return the fallback value since defaults is None
            assert result == 0.99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
