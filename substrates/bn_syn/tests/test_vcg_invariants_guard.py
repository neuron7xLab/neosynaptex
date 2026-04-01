"""
Guard tests for VCG invariants defined in docs/VCG.md

These tests enforce the hard invariants specified for the Verified Contribution Gating module:
- I1: Support scores are deterministic given same observable log + parameters
- I2: Support score is monotonic non-increasing while contribution < threshold
- I3: Recovery is possible (no permanent exclusion) if contribution >= threshold
- I4: VCG remains side-effect free on the simulation core

Reference: docs/VCG.md:46-50
"""

from __future__ import annotations

import pytest

from bnsyn.vcg import VCGParams, allocation_multiplier, update_support_level


@pytest.fixture
def default_vcg_params() -> VCGParams:
    """Default VCG parameters for testing."""
    return VCGParams(
        theta_c=10.0,  # Minimum contribution threshold
        alpha_down=0.1,  # Decrease rate
        alpha_up=0.05,  # Recovery rate
        epsilon=0.1,  # Stability floor
    )


class TestVCGInvariantI1_Determinism:
    """
    I1: Support scores are deterministic given same observable log + parameters
    Reference: docs/VCG.md:47
    """

    def test_deterministic_replay_identical_logs(self, default_vcg_params: VCGParams) -> None:
        """Replaying same event log yields identical support score traces."""
        # Define a deterministic event log
        contributions = [5.0, 8.0, 12.0, 3.0, 15.0, 20.0, 7.0, 11.0]

        # Replay on first instance
        support = 1.0
        support_trace_1 = []
        for contrib in contributions:
            support = update_support_level(contrib, support, default_vcg_params)
            support_trace_1.append(support)

        # Replay on second instance
        support = 1.0
        support_trace_2 = []
        for contrib in contributions:
            support = update_support_level(contrib, support, default_vcg_params)
            support_trace_2.append(support)

        # I1: Traces must be bitwise identical
        assert support_trace_1 == support_trace_2, (
            f"I1 violated: determinism failed\nTrace1: {support_trace_1}\nTrace2: {support_trace_2}"
        )

    def test_deterministic_with_different_initial_states(
        self, default_vcg_params: VCGParams
    ) -> None:
        """Different initial support values but same updates yield deterministic results."""
        contributions = [15.0, 20.0, 25.0]

        # Apply same updates starting from 1.0
        support1 = 1.0
        for contrib in contributions:
            support1 = update_support_level(contrib, support1, default_vcg_params)

        # Apply same updates starting from 0.5
        support2 = 0.5
        for contrib in contributions:
            support2 = update_support_level(contrib, support2, default_vcg_params)

        # Both should increase after high contributions
        assert support1 > 0.95, f"I1: Support1 did not recover properly: {support1}"
        assert support2 > 0.5, f"I1: Support2 did not recover properly: {support2}"

    def test_determinism_under_seed_control(self, default_vcg_params: VCGParams) -> None:
        """Determinism holds for repeated deterministic inputs."""
        contributions = [9.0, 10.0, 11.0, 9.5, 10.5, 10.0, 8.0, 12.0, 10.0, 9.0]

        support = 1.0
        support_trace_1 = []
        for contrib in contributions:
            support = update_support_level(contrib, support, default_vcg_params)
            support_trace_1.append(support)

        support = 1.0
        support_trace_2 = []
        for contrib in contributions:
            support = update_support_level(contrib, support, default_vcg_params)
            support_trace_2.append(support)

        assert support_trace_1 == support_trace_2, "I1 violated: deterministic replay failed"


class TestVCGInvariantI2_MonotonicDecrease:
    """
    I2: Support score is monotonic non-increasing while contribution < threshold
    Reference: docs/VCG.md:48
    """

    def test_monotonic_decrease_below_threshold(self, default_vcg_params: VCGParams) -> None:
        """Support decreases monotonically when contribution < theta_c."""
        low_contrib = default_vcg_params.theta_c - 1.0  # Below threshold

        support = 1.0
        support_history = [support]

        # Apply low contribution updates
        for _ in range(20):
            support = update_support_level(low_contrib, support, default_vcg_params)
            support_history.append(support)

        # I2: Support must be monotonically non-increasing
        for i in range(len(support_history) - 1):
            assert support_history[i + 1] <= support_history[i], (
                f"I2 violated: support increased at step {i}: {support_history[i]} -> {support_history[i + 1]}"
            )

    def test_no_decrease_at_floor(self, default_vcg_params: VCGParams) -> None:
        """Support stops decreasing at epsilon floor."""
        low_contrib = default_vcg_params.theta_c - 1.0

        # Drive support to floor
        support = 1.0
        for _ in range(100):
            support = update_support_level(low_contrib, support, default_vcg_params)

        # I2: Support should be at or near floor
        assert support >= 0.0, f"I2 violated: support went negative: {support}"
        assert support <= default_vcg_params.epsilon + 0.01, (
            f"I2 violated: support did not reach floor: {support}"
        )

    def test_strict_decrease_away_from_floor(self, default_vcg_params: VCGParams) -> None:
        """Support strictly decreases when above floor and contrib < threshold."""
        low_contrib = default_vcg_params.theta_c - 5.0

        support_prev = 1.0

        # Take one step
        support_new = update_support_level(low_contrib, support_prev, default_vcg_params)

        # I2: Must decrease (not just non-increase)
        assert support_new < support_prev, (
            f"I2 violated: support did not decrease: {support_prev} -> {support_new}"
        )


class TestVCGInvariantI3_RecoveryPossible:
    """
    I3: Recovery is possible (no permanent exclusion) if contribution >= threshold
    Reference: docs/VCG.md:49
    """

    def test_recovery_from_low_support(self, default_vcg_params: VCGParams) -> None:
        """Agent can recover from low support by sustained high contribution."""
        # Drive support to floor
        support = 1.0
        for _ in range(50):
            support = update_support_level(
                default_vcg_params.theta_c - 5.0, support, default_vcg_params
            )

        support_at_floor = support
        assert support_at_floor < 0.5, "Setup: support should be low"

        # Now apply high contribution
        high_contrib = default_vcg_params.theta_c + 5.0
        for _ in range(50):
            support = update_support_level(high_contrib, support, default_vcg_params)

        support_recovered = support

        # I3: Support should have recovered significantly
        assert support_recovered > support_at_floor, (
            f"I3 violated: no recovery after high contribution: {support_at_floor} -> {support_recovered}"
        )
        assert support_recovered > 0.7, f"I3 violated: recovery insufficient: {support_recovered}"

    def test_no_permanent_exclusion(self, default_vcg_params: VCGParams) -> None:
        """No agent is permanently excluded; recovery always possible."""
        support = 0.0  # Start at floor

        # Apply sustained high contribution
        high_contrib = default_vcg_params.theta_c + 10.0
        for _ in range(100):
            support = update_support_level(high_contrib, support, default_vcg_params)

        # I3: Agent must be able to recover to near-maximum support
        assert support >= 0.8, f"I3 violated: permanent exclusion detected, support={support}"

    def test_recovery_is_gradual(self, default_vcg_params: VCGParams) -> None:
        """Recovery rate is bounded by alpha_up (gradual increase)."""
        # Drive to floor
        support = 1.0
        for _ in range(50):
            support = update_support_level(0.0, support, default_vcg_params)

        support_start = support

        # Apply one high contribution update
        support_after = update_support_level(
            default_vcg_params.theta_c + 10.0, support_start, default_vcg_params
        )

        # I3: Increase should be bounded by alpha_up
        increase = support_after - support_start
        assert 0.0 <= increase <= default_vcg_params.alpha_up + 0.01, (
            f"I3 violated: recovery rate exceeded alpha_up: {increase} > {default_vcg_params.alpha_up}"
        )


class TestVCGInvariantI4_SideEffectFree:
    """
    I4: VCG remains side-effect free on the simulation core
    Reference: docs/VCG.md:50
    NOTE: Production VCG is currently a pure utility module; tests verify purity only.
    """

    def test_vcg_does_not_mutate_external_state(self, default_vcg_params: VCGParams) -> None:
        """VCG functions are pure with respect to their inputs."""
        support = 0.8
        contrib = default_vcg_params.theta_c - 1.0
        params_before = default_vcg_params

        support_after = update_support_level(contrib, support, default_vcg_params)
        support_after_repeat = update_support_level(contrib, support, default_vcg_params)
        alloc = allocation_multiplier(support_after, default_vcg_params)

        assert default_vcg_params is params_before
        assert support == 0.8
        assert support_after == support_after_repeat
        assert 0.0 <= alloc <= 1.0

    def test_vcg_is_query_safe(self, default_vcg_params: VCGParams) -> None:
        """Querying allocation multiplier does not change state."""
        # Update once
        support = update_support_level(10.0, 1.0, default_vcg_params)

        # Query multiple times
        support1 = allocation_multiplier(support, default_vcg_params)
        support2 = allocation_multiplier(support, default_vcg_params)
        support3 = allocation_multiplier(support, default_vcg_params)

        # I4: Queries should not alter state
        assert support1 == support2 == support3, (
            f"I4 violated: query changed state {support1}, {support2}, {support3}"
        )

    def test_vcg_disabling_preserves_core_simulation(self, default_vcg_params: VCGParams) -> None:
        """VCG disabled corresponds to identity allocation multiplier."""
        support = 1.0
        alloc = allocation_multiplier(support, default_vcg_params)
        assert alloc == 1.0, "I4 violated: disabled VCG should yield alloc=1.0"


class TestVCGInvariantComposite:
    """
    Test that all four VCG invariants hold simultaneously.
    """

    def test_all_vcg_invariants_hold_simultaneously(self, default_vcg_params: VCGParams) -> None:
        """All four VCG invariants must hold throughout simulation."""
        support = 1.0

        # Define a realistic contribution sequence
        contributions = [
            12.0,
            15.0,
            8.0,
            5.0,  # Starts high, then drops
            3.0,
            2.0,
            1.0,  # Low contributions
            15.0,
            20.0,
            25.0,  # Recovery
        ]

        # Track determinism (I1)
        support_trace = []

        for i, contrib in enumerate(contributions):
            support_before = support

            # Update
            support = update_support_level(contrib, support, default_vcg_params)
            support_trace.append(support)

            # I2: Check monotonicity when contrib < threshold
            if contrib < default_vcg_params.theta_c:
                assert support <= support_before, (
                    f"Step {i}: I2 violated (contrib={contrib} < {default_vcg_params.theta_c})"
                )

            # I3: Check recovery is possible
            if contrib >= default_vcg_params.theta_c:
                # Support should not decrease (recovery or stable)
                assert support >= support_before - 0.01, f"Step {i}: I3 violated (no recovery)"

            # I4: VCG should not affect this test's external variables
            # (implicitly tested by not mutating contrib or theta_c)

        # I1: Replay should give same trace
        support_replay = 1.0
        support_trace_replay = []
        for contrib in contributions:
            support_replay = update_support_level(contrib, support_replay, default_vcg_params)
            support_trace_replay.append(support_replay)

        assert support_trace == support_trace_replay, (
            "I1 violated: determinism failed in composite test"
        )


class TestVCGAcceptanceCriteria:
    """
    Test acceptance criteria from docs/VCG.md:59-62
    - A1: Replaying same event log yields identical S_i(t) traces (bitwise)
    - A2: Agent with C_i < θ_C for k consecutive windows shows strictly decreasing S_i
    - A3: Agent regains S_i → 1 after sustained C_i ≥ θ_C
    - A4: Disabling VCG yields allocation identity (core integration not present)
    """

    def test_A1_bitwise_replay(self, default_vcg_params: VCGParams) -> None:
        """A1: Replaying same event log yields identical traces."""
        contributions = [10.0, 5.0, 15.0, 3.0, 20.0]

        support1 = 1.0
        trace1 = [support1]
        for c in contributions:
            support1 = update_support_level(c, support1, default_vcg_params)
            trace1.append(support1)

        support2 = 1.0
        trace2 = [support2]
        for c in contributions:
            support2 = update_support_level(c, support2, default_vcg_params)
            trace2.append(support2)

        assert trace1 == trace2, "A1 violated: bitwise replay failed"

    def test_A2_strictly_decreasing_below_threshold(self, default_vcg_params: VCGParams) -> None:
        """A2: Agent with C_i < θ_C for k windows shows strictly decreasing S_i."""
        low_contrib = default_vcg_params.theta_c - 2.0
        support = 1.0

        # Apply 5 consecutive low contributions
        for _ in range(5):
            support_prev = support
            support = update_support_level(low_contrib, support, default_vcg_params)
            assert support < support_prev or support == 0.0, "A2 violated: support not decreasing"

    def test_A3_regain_support_to_one(self, default_vcg_params: VCGParams) -> None:
        """A3: Agent regains S_i → 1 after sustained high contribution."""
        high_contrib = default_vcg_params.theta_c + 10.0

        support = 0.5
        # Apply sustained high contribution
        for _ in range(100):
            support = update_support_level(high_contrib, support, default_vcg_params)

        assert support >= 0.95, f"A3 violated: failed to regain S_i → 1, got {support}"

    def test_A4_disabling_vcg_yields_identity(self, default_vcg_params: VCGParams) -> None:
        """A4: Disabling VCG (support=1.0 always) yields unmodified allocation."""
        # Simulate "disabled" VCG where support is always 1.0

        # With support = 1.0, allocation should be 1.0
        alloc = allocation_multiplier(1.0, default_vcg_params)
        assert alloc == 1.0, "A4 violated: disabled VCG should yield alloc=1.0"
