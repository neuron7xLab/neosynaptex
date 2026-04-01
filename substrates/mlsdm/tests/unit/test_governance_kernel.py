"""
Unit Tests for GovernanceKernel

Tests for governance kernel read-only proxies and reset functionality.
"""

import numpy as np

from mlsdm.core.governance_kernel import GovernanceKernel


class TestReadOnlyProxies:
    """Test read-only proxy classes for kernel components."""

    def test_synaptic_ro_lambda_l3(self):
        """Test SynapticRO.lambda_l3 property."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        synaptic_ro = kernel.synaptic_ro

        # Access lambda_l3 property
        lambda_l3 = synaptic_ro.lambda_l3
        assert isinstance(lambda_l3, float)
        assert lambda_l3 > 0

    def test_synaptic_ro_theta_l2(self):
        """Test SynapticRO.theta_l2 property."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        synaptic_ro = kernel.synaptic_ro

        # Access theta_l2 property
        theta_l2 = synaptic_ro.theta_l2
        assert isinstance(theta_l2, float)
        assert theta_l2 > 0

    def test_synaptic_ro_gating12(self):
        """Test SynapticRO.gating12 property."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        synaptic_ro = kernel.synaptic_ro

        # Access gating12 property
        gating12 = synaptic_ro.gating12
        assert isinstance(gating12, float)
        assert 0 <= gating12 <= 1

    def test_synaptic_ro_gating23(self):
        """Test SynapticRO.gating23 property."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        synaptic_ro = kernel.synaptic_ro

        # Access gating23 property
        gating23 = synaptic_ro.gating23
        assert isinstance(gating23, float)
        assert 0 <= gating23 <= 1

    def test_synaptic_ro_to_dict(self):
        """Test SynapticRO.to_dict() method."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        synaptic_ro = kernel.synaptic_ro

        # Call to_dict method
        state_dict = synaptic_ro.to_dict()
        assert isinstance(state_dict, dict)
        assert "lambda_l1" in state_dict or "dim" in state_dict

    def test_moral_ro_get_state(self):
        """Test MoralRO.get_state() method."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        moral_ro = kernel.moral_ro

        # Call get_state method
        state = moral_ro.get_state()
        assert isinstance(state, dict)

    def test_pelm_ro_detect_corruption(self):
        """Test PelmRO.detect_corruption() method."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        pelm_ro = kernel.pelm_ro

        # Call detect_corruption method
        is_corrupted = pelm_ro.detect_corruption()
        assert isinstance(is_corrupted, bool)


class TestGovernanceKernelReset:
    """Test GovernanceKernel reset functionality."""

    def test_reset_with_initial_moral_threshold(self):
        """Test reset with initial_moral_threshold parameter."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3,
            initial_moral_threshold=0.5
        )

        # Reset with new threshold
        kernel.reset(initial_moral_threshold=0.6)

        # Verify the kernel still works after reset
        assert kernel.moral_ro.threshold >= 0

    def test_reset_with_synaptic_config(self):
        """Test reset with synaptic_config parameter."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )

        # Create a simple config-like object (could be None in practice)
        # Since we're testing code coverage, we just need to pass the parameter
        from mlsdm.config import SYNAPTIC_MEMORY_DEFAULTS
        config = SYNAPTIC_MEMORY_DEFAULTS

        # Reset with synaptic config
        kernel.reset(synaptic_config=config)

        # Verify the kernel still works after reset
        assert kernel.synaptic_ro is not None

    def test_reset_with_all_optional_params(self):
        """Test reset with both initial_moral_threshold and synaptic_config."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )

        # Import config if available
        try:
            from mlsdm.config import SYNAPTIC_MEMORY_DEFAULTS
            config = SYNAPTIC_MEMORY_DEFAULTS
        except ImportError:
            config = None

        # Reset with both optional parameters
        kernel.reset(
            initial_moral_threshold=0.6,
            synaptic_config=config
        )

        # Verify the kernel still works after reset
        assert kernel.moral_ro is not None
        assert kernel.synaptic_ro is not None


class TestGovernanceKernelCapabilities:
    """Test capability-based access control."""

    def test_capability_validation_through_cognitive_controller(self):
        """Test capability validation by calling methods through cognitive_controller."""
        from mlsdm.core.cognitive_controller import CognitiveController

        # CognitiveController is in the allowlist and will call kernel methods
        controller = CognitiveController()

        # Process an event which will call kernel.moral_adapt and kernel.memory_commit internally
        vector = np.random.randn(384).astype(np.float32)
        result = controller.process_event(vector, moral_value=0.8)

        assert result is not None
        assert isinstance(result, dict)

    def test_capability_nonce_mismatch_raises_permission_error(self):
        """Test that capability with wrong nonce raises PermissionError."""
        from mlsdm.core.governance_kernel import Capability

        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )

        # Create a fake capability with wrong nonce hash
        bad_cap = Capability(
            perms=frozenset(["MUTATE_MORAL_THRESHOLD"]),
            kernel_nonce_hash="wrong_nonce_hash"
        )

        import pytest

        with pytest.raises(PermissionError) as exc_info:
            kernel.moral_adapt(accepted=True, cap=bad_cap)

        assert "nonce mismatch" in str(exc_info.value)

    def test_capability_missing_permission_raises_error(self):
        """Test that capability without required permission raises PermissionError."""
        from mlsdm.core.governance_kernel import Capability

        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )

        # Create a capability with correct nonce but missing permission
        # Access private _cap_hash for testing
        correct_nonce = kernel._cap_hash

        bad_cap = Capability(
            perms=frozenset(["WRONG_PERM"]),  # Missing MUTATE_MORAL_THRESHOLD
            kernel_nonce_hash=correct_nonce
        )

        import pytest

        with pytest.raises(PermissionError) as exc_info:
            kernel.moral_adapt(accepted=True, cap=bad_cap)

        assert "missing permission" in str(exc_info.value)

    def test_assert_can_mutate_blocks_unauthorized_caller(self, monkeypatch):
        """Test that mutations from unauthorized callers are blocked."""
        import pytest

        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )

        # Mock inspect.stack to return an unauthorized module
        def mock_stack():
            class MockFrame:
                def __init__(self):
                    self.f_globals = {"__name__": "unauthorized.module"}

            class MockFrameInfo:
                def __init__(self):
                    self.frame = MockFrame()

            return [MockFrameInfo(), MockFrameInfo(), MockFrameInfo()]

        import inspect
        monkeypatch.setattr(inspect, "stack", mock_stack)

        with pytest.raises(PermissionError) as exc_info:
            kernel.moral_adapt(accepted=True)  # No capability provided

        assert "Kernel mutation blocked" in str(exc_info.value)

    def test_issue_capability_blocks_unauthorized_caller(self, monkeypatch):
        """Test that issue_capability blocks unauthorized callers."""
        import pytest

        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )

        # Mock inspect.stack to return an unauthorized module
        def mock_stack():
            class MockFrame:
                def __init__(self):
                    self.f_globals = {"__name__": "unauthorized.module"}

            class MockFrameInfo:
                def __init__(self):
                    self.frame = MockFrame()

            return [MockFrameInfo(), MockFrameInfo()]

        import inspect
        monkeypatch.setattr(inspect, "stack", mock_stack)

        with pytest.raises(PermissionError) as exc_info:
            kernel.issue_capability(perms={"MUTATE_MORAL_THRESHOLD"})

        assert "Cannot issue capability from" in str(exc_info.value)

    def test_issue_capability_allows_internal_caller(self, monkeypatch):
        """Test that issue_capability allows callers from the internal allowlist."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )

        # Mock inspect.stack to return an allowed module
        def mock_stack():
            class MockFrame:
                def __init__(self):
                    self.f_globals = {"__name__": "mlsdm.core.cognitive_controller"}

            class MockFrameInfo:
                def __init__(self):
                    self.frame = MockFrame()

            return [MockFrameInfo(), MockFrameInfo()]

        import inspect
        monkeypatch.setattr(inspect, "stack", mock_stack)

        cap = kernel.issue_capability(perms={"MUTATE_MORAL_THRESHOLD"})

        assert cap is not None
        assert "MUTATE_MORAL_THRESHOLD" in cap.perms


class TestReadOnlyProxiesAdditionalMethods:
    """Test additional read-only proxy methods for coverage."""

    def test_moral_ro_get_current_threshold(self):
        """Test MoralRO.get_current_threshold() method."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        moral_ro = kernel.moral_ro

        threshold = moral_ro.get_current_threshold()
        assert isinstance(threshold, float)
        assert 0 <= threshold <= 1

    def test_moral_ro_get_ema_value(self):
        """Test MoralRO.get_ema_value() method."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        moral_ro = kernel.moral_ro

        ema = moral_ro.get_ema_value()
        assert isinstance(ema, float)
        assert 0 <= ema <= 1

    def test_synaptic_ro_get_state(self):
        """Test SynapticRO.get_state() method."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        synaptic_ro = kernel.synaptic_ro

        state = synaptic_ro.get_state()
        assert isinstance(state, tuple)
        assert len(state) == 3

    def test_pelm_ro_size_property(self):
        """Test PelmRO.size property."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        pelm_ro = kernel.pelm_ro

        size = pelm_ro.size
        assert isinstance(size, int)
        assert size >= 0

    def test_rhythm_ro_get_state_label(self):
        """Test RhythmRO.get_state_label() method."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        rhythm_ro = kernel.rhythm_ro

        label = rhythm_ro.get_state_label()
        assert isinstance(label, str)
        assert label in ("wake", "sleep")

    def test_rhythm_ro_get_current_phase(self):
        """Test RhythmRO.get_current_phase() method."""
        kernel = GovernanceKernel(
            dim=10,
            capacity=100,
            wake_duration=8,
            sleep_duration=3
        )
        rhythm_ro = kernel.rhythm_ro

        phase = rhythm_ro.get_current_phase()
        assert isinstance(phase, str)
        assert phase in ("wake", "sleep")
