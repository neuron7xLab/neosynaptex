"""
Tests for MultiLevelSynapticMemory calibration via YAML config.

Tests cover:
- YAML → calibration.py → MultiLevelSynapticMemory config path
- Verification that changing λ (lambda) affects forgetting/decay rate
- Verification that changing θ (theta) / gating affects activation thresholds
- Backward compatibility with defaults when YAML config is absent
"""

import numpy as np
import pytest

from mlsdm.config import (
    SYNAPTIC_MEMORY_DEFAULTS,
    SynapticMemoryCalibration,
    get_synaptic_memory_config,
)
from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory


class TestGetSynapticMemoryConfig:
    """Tests for get_synaptic_memory_config factory function."""

    def test_returns_defaults_when_no_yaml(self):
        """Test that defaults are returned when no YAML config provided."""
        config = get_synaptic_memory_config(None)
        assert config.lambda_l1 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l1
        assert config.lambda_l2 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l2
        assert config.lambda_l3 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l3
        assert config.theta_l1 == SYNAPTIC_MEMORY_DEFAULTS.theta_l1
        assert config.theta_l2 == SYNAPTIC_MEMORY_DEFAULTS.theta_l2
        assert config.gating12 == SYNAPTIC_MEMORY_DEFAULTS.gating12
        assert config.gating23 == SYNAPTIC_MEMORY_DEFAULTS.gating23

    def test_returns_defaults_when_empty_yaml(self):
        """Test that defaults are returned when YAML config is empty."""
        config = get_synaptic_memory_config({})
        assert config.lambda_l1 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l1

    def test_returns_defaults_when_no_multi_level_memory_section(self):
        """Test that defaults are returned when multi_level_memory section is missing."""
        yaml_config = {"dimension": 384, "some_other_config": True}
        config = get_synaptic_memory_config(yaml_config)
        assert config.lambda_l1 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l1

    def test_merges_partial_yaml_with_defaults(self):
        """Test that partial YAML config merges with defaults."""
        yaml_config = {
            "multi_level_memory": {
                "lambda_l1": 0.3,  # Override
                # Other fields should come from defaults
            }
        }
        config = get_synaptic_memory_config(yaml_config)
        assert config.lambda_l1 == 0.3  # From YAML
        assert config.lambda_l2 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l2  # Default
        assert config.lambda_l3 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l3  # Default

    def test_full_yaml_override(self):
        """Test that all YAML values override defaults."""
        yaml_config = {
            "multi_level_memory": {
                "lambda_l1": 0.7,
                "lambda_l2": 0.3,
                "lambda_l3": 0.05,
                "theta_l1": 2.0,
                "theta_l2": 4.0,
                "gating12": 0.6,
                "gating23": 0.4,
            }
        }
        config = get_synaptic_memory_config(yaml_config)
        assert config.lambda_l1 == 0.7
        assert config.lambda_l2 == 0.3
        assert config.lambda_l3 == 0.05
        assert config.theta_l1 == 2.0
        assert config.theta_l2 == 4.0
        assert config.gating12 == 0.6
        assert config.gating23 == 0.4


class TestMultiLevelSynapticMemoryWithConfig:
    """Tests for MultiLevelSynapticMemory with config parameter."""

    def test_uses_config_when_provided(self):
        """Test that memory uses config parameter when provided."""
        custom_config = SynapticMemoryCalibration(
            lambda_l1=0.7,
            lambda_l2=0.3,
            lambda_l3=0.05,
            theta_l1=2.0,
            theta_l2=4.0,
            gating12=0.6,
            gating23=0.4,
        )
        memory = MultiLevelSynapticMemory(dimension=10, config=custom_config)
        assert memory.lambda_l1 == 0.7
        assert memory.lambda_l2 == 0.3
        assert memory.lambda_l3 == 0.05
        assert memory.theta_l1 == 2.0
        assert memory.theta_l2 == 4.0
        assert memory.gating12 == 0.6
        assert memory.gating23 == 0.4

    def test_explicit_args_override_config(self):
        """Test that explicit arguments override config values."""
        custom_config = SynapticMemoryCalibration(
            lambda_l1=0.7,
            lambda_l2=0.3,
        )
        memory = MultiLevelSynapticMemory(
            dimension=10,
            lambda_l1=0.2,  # Override config
            config=custom_config,
        )
        assert memory.lambda_l1 == 0.2  # From explicit arg
        assert memory.lambda_l2 == 0.3  # From config

    def test_defaults_used_without_config(self):
        """Test that SYNAPTIC_MEMORY_DEFAULTS are used without config."""
        memory = MultiLevelSynapticMemory(dimension=10)
        assert memory.lambda_l1 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l1
        assert memory.lambda_l2 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l2
        assert memory.lambda_l3 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l3


class TestLambdaAffectsForgettingRate:
    """Tests proving that changing λ (lambda) affects forgetting/decay rate.

    Scenario A: Compare default λ vs custom λ to verify:
    - Higher λ = faster decay
    - Lower λ = slower decay (better retention)
    """

    def test_higher_lambda_faster_decay(self):
        """Test that higher λ results in faster decay (lower retention)."""
        dim = 10
        num_decay_steps = 5

        # Config with default λ values from SYNAPTIC_MEMORY_DEFAULTS
        mem_default = MultiLevelSynapticMemory(
            dimension=dim,
            config=SYNAPTIC_MEMORY_DEFAULTS,
        )

        # Config with higher λ_l1 = 0.90 (very fast decay)
        fast_decay_config = SynapticMemoryCalibration(
            lambda_l1=0.90,  # Higher = faster decay
            lambda_l2=SYNAPTIC_MEMORY_DEFAULTS.lambda_l2,
            lambda_l3=SYNAPTIC_MEMORY_DEFAULTS.lambda_l3,
            theta_l1=SYNAPTIC_MEMORY_DEFAULTS.theta_l1,
            theta_l2=SYNAPTIC_MEMORY_DEFAULTS.theta_l2,
            gating12=SYNAPTIC_MEMORY_DEFAULTS.gating12,
            gating23=SYNAPTIC_MEMORY_DEFAULTS.gating23,
        )
        mem_fast_decay = MultiLevelSynapticMemory(
            dimension=dim,
            config=fast_decay_config,
        )

        # Add identical initial event to both memories
        initial_event = np.ones(dim, dtype=np.float32) * 5.0
        mem_default.update(initial_event)
        mem_fast_decay.update(initial_event)

        # Record initial L1 norms immediately after first update
        l1_default_initial, _, _ = mem_default.get_state()
        l1_fast_initial, _, _ = mem_fast_decay.get_state()
        norm_default_initial = np.linalg.norm(l1_default_initial)
        norm_fast_initial = np.linalg.norm(l1_fast_initial)

        # Apply decay by updating with zero events
        zero_event = np.zeros(dim, dtype=np.float32)
        for _ in range(num_decay_steps):
            mem_default.update(zero_event)
            mem_fast_decay.update(zero_event)

        # Check final L1 norms after decay
        l1_default_final, _, _ = mem_default.get_state()
        l1_fast_final, _, _ = mem_fast_decay.get_state()
        norm_default_final = np.linalg.norm(l1_default_final)
        norm_fast_final = np.linalg.norm(l1_fast_final)

        # Assert: faster decay (higher λ) should have lower final norm
        assert norm_fast_final < norm_default_final, (
            f"Higher λ should result in faster decay. "
            f"Fast decay norm: {norm_fast_final}, Default norm: {norm_default_final}"
        )

        # Assert: both should have decayed from initial
        assert norm_default_final < norm_default_initial
        assert norm_fast_final < norm_fast_initial

    def test_lower_lambda_slower_decay(self):
        """Test that lower λ results in slower decay (better retention)."""
        dim = 10
        num_decay_steps = 5

        # Config with default λ values from SYNAPTIC_MEMORY_DEFAULTS
        mem_default = MultiLevelSynapticMemory(
            dimension=dim,
            config=SYNAPTIC_MEMORY_DEFAULTS,
        )

        # Config with lower λ_l1 = 0.10 (slow decay)
        slow_decay_config = SynapticMemoryCalibration(
            lambda_l1=0.10,  # Lower = slower decay
            lambda_l2=SYNAPTIC_MEMORY_DEFAULTS.lambda_l2,
            lambda_l3=SYNAPTIC_MEMORY_DEFAULTS.lambda_l3,
            theta_l1=SYNAPTIC_MEMORY_DEFAULTS.theta_l1,
            theta_l2=SYNAPTIC_MEMORY_DEFAULTS.theta_l2,
            gating12=SYNAPTIC_MEMORY_DEFAULTS.gating12,
            gating23=SYNAPTIC_MEMORY_DEFAULTS.gating23,
        )
        mem_slow_decay = MultiLevelSynapticMemory(
            dimension=dim,
            config=slow_decay_config,
        )

        # Add identical initial event to both memories
        initial_event = np.ones(dim, dtype=np.float32) * 5.0
        mem_default.update(initial_event)
        mem_slow_decay.update(initial_event)

        # Apply decay by updating with zero events
        zero_event = np.zeros(dim, dtype=np.float32)
        for _ in range(num_decay_steps):
            mem_default.update(zero_event)
            mem_slow_decay.update(zero_event)

        # Check final L1 norms after decay
        l1_default_final, _, _ = mem_default.get_state()
        l1_slow_final, _, _ = mem_slow_decay.get_state()
        norm_default_final = np.linalg.norm(l1_default_final)
        norm_slow_final = np.linalg.norm(l1_slow_final)

        # Assert: slower decay (lower λ) should have higher final norm
        assert norm_slow_final > norm_default_final, (
            f"Lower λ should result in slower decay (higher retention). "
            f"Slow decay norm: {norm_slow_final}, Default norm: {norm_default_final}"
        )

    def test_yaml_lambda_affects_decay(self):
        """Test that λ from YAML config affects decay rate."""
        dim = 10
        num_decay_steps = 5

        # Simulate YAML config with custom λ values
        yaml_fast = {"multi_level_memory": {"lambda_l1": 0.90}}
        yaml_slow = {"multi_level_memory": {"lambda_l1": 0.10}}

        config_fast = get_synaptic_memory_config(yaml_fast)
        config_slow = get_synaptic_memory_config(yaml_slow)

        mem_fast = MultiLevelSynapticMemory(dimension=dim, config=config_fast)
        mem_slow = MultiLevelSynapticMemory(dimension=dim, config=config_slow)

        # Add identical events
        initial_event = np.ones(dim, dtype=np.float32) * 5.0
        mem_fast.update(initial_event)
        mem_slow.update(initial_event)

        # Apply decay
        zero_event = np.zeros(dim, dtype=np.float32)
        for _ in range(num_decay_steps):
            mem_fast.update(zero_event)
            mem_slow.update(zero_event)

        # Compare final states
        l1_fast, _, _ = mem_fast.get_state()
        l1_slow, _, _ = mem_slow.get_state()

        assert np.linalg.norm(l1_fast) < np.linalg.norm(
            l1_slow
        ), "YAML config with higher λ should result in faster decay"


class TestThetaGatingAffectsActivation:
    """Tests proving that changing θ (theta) and gating affects activation.

    Scenario B: Compare low vs high thresholds to verify:
    - Low θ = easier activation (more transfer to L2/L3)
    - High θ = harder activation (less transfer)
    - Higher gating = more transfer per step when threshold is exceeded
    """

    def test_low_threshold_more_transfer(self):
        """Test that lower θ results in more transfer to L2.

        With low theta, even small L1 values exceed the threshold,
        triggering transfer to L2. With high theta, L1 must accumulate
        more before any transfer occurs.
        """
        dim = 10

        # Config with low θ_l1 = 0.5 (easy transfer)
        low_theta_config = SynapticMemoryCalibration(
            lambda_l1=0.1,  # Low decay to preserve signal
            lambda_l2=0.01,  # Very low decay in L2 to accumulate
            lambda_l3=0.01,
            theta_l1=0.5,  # Low threshold - easy transfer
            theta_l2=100.0,  # High to prevent L2→L3 transfer
            gating12=0.3,  # Moderate gating
            gating23=0.0,  # No L2→L3 transfer
        )

        # Config with high θ_l1 = 10.0 (hard transfer)
        high_theta_config = SynapticMemoryCalibration(
            lambda_l1=0.1,
            lambda_l2=0.01,
            lambda_l3=0.01,
            theta_l1=10.0,  # High threshold - hard transfer
            theta_l2=100.0,
            gating12=0.3,
            gating23=0.0,
        )

        mem_low_theta = MultiLevelSynapticMemory(dimension=dim, config=low_theta_config)
        mem_high_theta = MultiLevelSynapticMemory(dimension=dim, config=high_theta_config)

        # Add events with small values (below high threshold but above low threshold)
        event = np.ones(dim, dtype=np.float32) * 1.0
        for _ in range(20):
            mem_low_theta.update(event)
            mem_high_theta.update(event)

        # Check L2 states
        _, l2_low, _ = mem_low_theta.get_state()
        _, l2_high, _ = mem_high_theta.get_state()

        norm_l2_low = np.linalg.norm(l2_low)
        norm_l2_high = np.linalg.norm(l2_high)

        # Assert: low threshold should allow transfer, high should block it
        assert norm_l2_low > norm_l2_high, (
            f"Lower θ should result in more L2 transfer. "
            f"Low θ L2 norm: {norm_l2_low}, High θ L2 norm: {norm_l2_high}"
        )

    def test_gating_affects_transfer_amount(self):
        """Test that gating factor affects the amount of transfer.

        Higher gating means more of L1 is transferred to L2 when
        threshold is exceeded. We test with a single large input
        to see the immediate effect.
        """
        dim = 10

        # Config with low gating12 = 0.1
        low_gating_config = SynapticMemoryCalibration(
            lambda_l1=0.0001,  # Almost no decay
            lambda_l2=0.0001,  # Almost no decay
            lambda_l3=0.0001,
            theta_l1=0.1,  # Low threshold to ensure transfer happens
            theta_l2=1000.0,  # Prevent L2→L3
            gating12=0.1,  # Low gating - less transfer per step
            gating23=0.0,
        )

        # Config with high gating12 = 0.9
        high_gating_config = SynapticMemoryCalibration(
            lambda_l1=0.0001,
            lambda_l2=0.0001,
            lambda_l3=0.0001,
            theta_l1=0.1,
            theta_l2=1000.0,
            gating12=0.9,  # High gating - more transfer per step
            gating23=0.0,
        )

        mem_low_gating = MultiLevelSynapticMemory(dimension=dim, config=low_gating_config)
        mem_high_gating = MultiLevelSynapticMemory(dimension=dim, config=high_gating_config)

        # Add a single large event
        event = np.ones(dim, dtype=np.float32) * 10.0
        mem_low_gating.update(event)
        mem_high_gating.update(event)

        # Check L2 states after just one update
        _, l2_low, _ = mem_low_gating.get_state()
        _, l2_high, _ = mem_high_gating.get_state()

        norm_l2_low = np.linalg.norm(l2_low)
        norm_l2_high = np.linalg.norm(l2_high)

        # Assert: higher gating should transfer more in single step
        assert norm_l2_high > norm_l2_low, (
            f"Higher gating should result in more L2 transfer per step. "
            f"High gating L2 norm: {norm_l2_high}, Low gating L2 norm: {norm_l2_low}"
        )

    def test_yaml_theta_affects_activation(self):
        """Test that θ from YAML config affects activation thresholds."""
        dim = 10
        num_steps = 10

        # Simulate YAML configs
        yaml_low_theta = {
            "multi_level_memory": {
                "lambda_l1": 0.1,
                "theta_l1": 0.5,  # Low threshold
                "gating12": 0.5,
            }
        }
        yaml_high_theta = {
            "multi_level_memory": {
                "lambda_l1": 0.1,
                "theta_l1": 5.0,  # High threshold
                "gating12": 0.5,
            }
        }

        config_low = get_synaptic_memory_config(yaml_low_theta)
        config_high = get_synaptic_memory_config(yaml_high_theta)

        mem_low = MultiLevelSynapticMemory(dimension=dim, config=config_low)
        mem_high = MultiLevelSynapticMemory(dimension=dim, config=config_high)

        # Add events
        event = np.ones(dim, dtype=np.float32) * 2.0
        for _ in range(num_steps):
            mem_low.update(event)
            mem_high.update(event)

        # Compare L2 transfer
        _, l2_low, _ = mem_low.get_state()
        _, l2_high, _ = mem_high.get_state()

        assert np.linalg.norm(l2_low) > np.linalg.norm(
            l2_high
        ), "YAML config with lower θ should result in more L2 transfer"


class TestCognitiveControllerWithYAMLConfig:
    """Tests for CognitiveController using YAML config path."""

    def test_controller_uses_yaml_config(self):
        """Test that CognitiveController uses YAML config for synaptic memory."""
        yaml_config = {
            "multi_level_memory": {
                "lambda_l1": 0.7,
                "theta_l1": 2.0,
            }
        }

        controller = CognitiveController(dim=10, yaml_config=yaml_config)

        assert controller.synaptic.lambda_l1 == 0.7
        assert controller.synaptic.theta_l1 == 2.0
        # Defaults for unspecified values
        assert controller.synaptic.lambda_l2 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l2

    def test_controller_uses_explicit_config(self):
        """Test that CognitiveController uses explicit synaptic_config."""
        custom_config = SynapticMemoryCalibration(
            lambda_l1=0.8,
            lambda_l2=0.4,
            lambda_l3=0.02,
            theta_l1=1.5,
            theta_l2=3.0,
            gating12=0.7,
            gating23=0.5,
        )

        controller = CognitiveController(dim=10, synaptic_config=custom_config)

        assert controller.synaptic.lambda_l1 == 0.8
        assert controller.synaptic.lambda_l2 == 0.4
        assert controller.synaptic.theta_l1 == 1.5

    def test_controller_explicit_config_overrides_yaml(self):
        """Test that synaptic_config takes precedence over yaml_config."""
        yaml_config = {
            "multi_level_memory": {
                "lambda_l1": 0.3,
            }
        }
        explicit_config = SynapticMemoryCalibration(
            lambda_l1=0.9,
        )

        controller = CognitiveController(
            dim=10,
            yaml_config=yaml_config,
            synaptic_config=explicit_config,
        )

        # Explicit config should win
        assert controller.synaptic.lambda_l1 == 0.9

    def test_controller_defaults_without_config(self):
        """Test that CognitiveController uses defaults without any config."""
        controller = CognitiveController(dim=10)

        assert controller.synaptic.lambda_l1 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l1
        assert controller.synaptic.lambda_l2 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l2
        assert controller.synaptic.theta_l1 == SYNAPTIC_MEMORY_DEFAULTS.theta_l1


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing code."""

    def test_memory_explicit_args_still_work(self):
        """Test that explicit argument passing still works."""
        memory = MultiLevelSynapticMemory(
            dimension=10,
            lambda_l1=0.3,
            lambda_l2=0.2,
            lambda_l3=0.05,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
        )
        assert memory.lambda_l1 == 0.3
        assert memory.lambda_l2 == 0.2

    def test_controller_without_new_args_works(self):
        """Test that CognitiveController without new args works."""
        controller = CognitiveController(
            dim=10,
            memory_threshold_mb=512.0,
            max_processing_time_ms=500.0,
        )
        assert controller.dim == 10
        assert controller.memory_threshold_mb == 512.0
        # Synaptic should use defaults
        assert controller.synaptic.lambda_l1 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l1

    def test_empty_yaml_uses_defaults(self):
        """Test that empty YAML config results in defaults being used."""
        controller = CognitiveController(dim=10, yaml_config={})
        assert controller.synaptic.lambda_l1 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l1

    def test_partial_yaml_merges_correctly(self):
        """Test that partial YAML config merges with defaults."""
        yaml_config = {
            "multi_level_memory": {
                "lambda_l1": 0.6,
                # Other fields should default
            }
        }
        controller = CognitiveController(dim=10, yaml_config=yaml_config)
        assert controller.synaptic.lambda_l1 == 0.6
        assert controller.synaptic.lambda_l2 == SYNAPTIC_MEMORY_DEFAULTS.lambda_l2
        assert controller.synaptic.theta_l1 == SYNAPTIC_MEMORY_DEFAULTS.theta_l1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
