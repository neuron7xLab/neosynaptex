"""
Security Tests for Capability-Enforced Governance Kernel

This test suite validates that the GovernanceKernel enforces capability-based
access control for mutating operations, ensuring that only authorized internal
modules can modify kernel state.
"""

import numpy as np
import pytest

from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.core.governance_kernel import Capability, GovernanceKernel


def test_direct_kernel_moral_adapt_is_blocked_without_cap():
    """Test that direct calls to moral_adapt are blocked without capability."""
    kernel = GovernanceKernel(
        dim=384,
        capacity=1000,
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.5,
    )

    # Direct call from test module should be blocked
    with pytest.raises(PermissionError) as exc_info:
        kernel.moral_adapt(accepted=True)

    assert "Kernel mutation blocked" in str(exc_info.value)


def test_direct_kernel_memory_commit_is_blocked_without_cap():
    """Test that direct calls to memory_commit are blocked without capability."""
    kernel = GovernanceKernel(
        dim=384,
        capacity=1000,
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.5,
    )

    vector = np.random.randn(384).astype(np.float32)

    # Direct call from test module should be blocked
    with pytest.raises(PermissionError) as exc_info:
        kernel.memory_commit(vector, phase=0.5)

    assert "Kernel mutation blocked" in str(exc_info.value)


def test_kernel_ro_proxies_do_not_expose_mutators():
    """Test that read-only proxies don't expose mutator methods."""
    kernel = GovernanceKernel(
        dim=384,
        capacity=1000,
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.5,
    )

    # Check that SynapticRO doesn't have update method
    assert not hasattr(kernel.synaptic_ro, "update"), (
        "SynapticRO should not expose 'update' method"
    )

    # Check that PelmRO doesn't have entangle method
    assert not hasattr(kernel.pelm_ro, "entangle"), (
        "PelmRO should not expose 'entangle' method"
    )

    # Verify read-only methods are still accessible
    assert hasattr(kernel.synaptic_ro, "state"), "SynapticRO should have 'state' method"
    assert hasattr(kernel.pelm_ro, "retrieve"), "PelmRO should have 'retrieve' method"
    assert hasattr(kernel.moral_ro, "evaluate"), "MoralRO should have 'evaluate' method"


def test_forged_capability_is_rejected():
    """Test that a forged capability with wrong nonce is rejected."""
    kernel = GovernanceKernel(
        dim=384,
        capacity=1000,
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.5,
    )

    # Create a fake capability with wrong nonce_hash
    forged_cap = Capability(
        perms=frozenset({"MUTATE_MORAL_THRESHOLD"}),
        kernel_nonce_hash="0" * 64,  # Fake hash
    )

    # Attempt to use forged capability should fail
    with pytest.raises(PermissionError) as exc_info:
        kernel.moral_adapt(accepted=True, cap=forged_cap)

    assert "Invalid capability: nonce mismatch" in str(exc_info.value)

    # Also test with memory_commit
    vector = np.random.randn(384).astype(np.float32)
    forged_cap_memory = Capability(
        perms=frozenset({"MEMORY_COMMIT"}),
        kernel_nonce_hash="0" * 64,  # Fake hash
    )

    with pytest.raises(PermissionError) as exc_info:
        kernel.memory_commit(vector, phase=0.5, cap=forged_cap_memory)

    assert "Invalid capability: nonce mismatch" in str(exc_info.value)


def test_internal_controller_path_still_works():
    """Test that internal controller path works without errors (smoke test)."""
    # This creates a CognitiveController which internally uses GovernanceKernel
    controller = CognitiveController(dim=384)

    # Create a test vector
    vector = np.random.randn(384).astype(np.float32)
    vector = vector / np.linalg.norm(vector)

    # Process an event through the controller
    # This internally calls kernel.moral_adapt and kernel.memory_commit
    result = controller.process_event(vector, moral_value=0.8)

    # Verify it worked - should be accepted if moral value is high enough
    # Note: might be rejected due to sleep phase, but should not raise PermissionError
    assert "note" in result, "Controller should return a result dict"
    assert "rejected" in result, "Controller should return rejection status"

    # If not emergency shutdown, we should be able to process multiple events
    if not controller.is_emergency_shutdown():
        for _ in range(5):
            result = controller.process_event(vector, moral_value=0.9)
            # Should not raise PermissionError
            assert "note" in result


def test_capability_missing_permission():
    """Test that a capability without required permission is rejected."""
    kernel = GovernanceKernel(
        dim=384,
        capacity=1000,
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.5,
    )

    # Create a capability with wrong permission
    wrong_perm_cap = Capability(
        perms=frozenset({"WRONG_PERMISSION"}),
        kernel_nonce_hash=kernel._cap_hash,  # Correct hash but wrong permission
    )

    # Attempt to use capability with missing permission should fail
    with pytest.raises(PermissionError) as exc_info:
        kernel.moral_adapt(accepted=True, cap=wrong_perm_cap)

    assert "Capability missing permission" in str(exc_info.value)
    assert "MUTATE_MORAL_THRESHOLD" in str(exc_info.value)


def test_issue_capability_from_external_is_blocked():
    """Test that external modules cannot issue capabilities."""
    kernel = GovernanceKernel(
        dim=384,
        capacity=1000,
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.5,
    )

    # Attempt to issue capability from test module should be blocked
    with pytest.raises(PermissionError) as exc_info:
        kernel.issue_capability({"MUTATE_MORAL_THRESHOLD"})

    assert "Cannot issue capability" in str(exc_info.value)
