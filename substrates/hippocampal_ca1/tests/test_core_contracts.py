"""
Tests for Core Contracts, Invariants, and Metrics.

This test suite validates:
1. Determinism - same seed produces identical outputs
2. State boundedness - state stays within limits after operations
3. Finite safety - no NaN/Inf in outputs
4. Shape safety - incorrect dimensions give controlled errors
5. Monotonic recall sanity - recall at least matches random baseline
6. Metrics stability - metrics return consistent dictionary structure
"""

from __future__ import annotations

import numpy as np
import pytest

from core import CA1Network
from core.contracts import (
    EncodeInput,
    MemoryState,
    Phase,
    RecallQuery,
    RecallResult,
    SimulationConfig,
    UpdateInput,
)
from core.invariants import (
    InvariantViolation,
    check_bounded,
    check_finite,
    check_non_negative,
    check_probability,
    check_shape_1d,
    check_spectral_radius,
    check_square_matrix,
    set_guards_enabled,
    validate_memory_state,
)
from core.metrics import (
    REPORT_KEYS,
    compute_report,
    drift_metric,
    memory_capacity_proxy,
    recall_accuracy_proxy,
    stability_metric,
    validate_report,
)


class TestDeterminism:
    """Test 1: Determinism - same seed produces identical outputs."""

    def test_ca1network_deterministic_with_same_seed(self) -> None:
        """Two CA1Network instances with same seed produce identical results."""
        seed = 42
        n_neurons = 10
        duration_ms = 50

        net1 = CA1Network(N=n_neurons, seed=seed, dt=0.5)
        result1 = net1.simulate(duration_ms=duration_ms)

        net2 = CA1Network(N=n_neurons, seed=seed, dt=0.5)
        result2 = net2.simulate(duration_ms=duration_ms)

        # Check all outputs are identical
        assert np.array_equal(result1["spikes"], result2["spikes"])
        assert np.allclose(result1["voltages"], result2["voltages"])
        assert np.allclose(result1["weights"], result2["weights"])
        assert np.array_equal(result1["time"], result2["time"])

    def test_ca1network_different_seeds_produce_different_results(self) -> None:
        """Different seeds produce different results."""
        n_neurons = 10
        duration_ms = 100

        net1 = CA1Network(N=n_neurons, seed=42, dt=0.5)
        result1 = net1.simulate(duration_ms=duration_ms)

        net2 = CA1Network(N=n_neurons, seed=123, dt=0.5)
        result2 = net2.simulate(duration_ms=duration_ms)

        # At least one output should differ
        assert not np.array_equal(result1["weights"], result2["weights"])

    def test_numpy_rng_determinism(self) -> None:
        """Verify numpy RNG is deterministic with seed."""
        seed = 42

        np.random.seed(seed)
        arr1 = np.random.randn(100)

        np.random.seed(seed)
        arr2 = np.random.randn(100)

        assert np.array_equal(arr1, arr2)


class TestStateBoundedness:
    """Test 2: State boundedness - state stays within limits."""

    def test_weights_bounded_after_simulation(self) -> None:
        """Weights remain bounded after simulation."""
        net = CA1Network(N=20, seed=42, dt=0.5)
        result = net.simulate(duration_ms=100)

        weights = result["weights"]

        # Weights should be finite and reasonably bounded
        assert np.all(np.isfinite(weights))
        assert np.all(weights >= 0)  # Non-negative for lognormal init
        assert np.all(weights < 100)  # Reasonable upper bound

    def test_voltages_bounded_after_simulation(self) -> None:
        """Voltages remain in physiologically plausible range."""
        net = CA1Network(N=20, seed=42, dt=0.5)
        result = net.simulate(duration_ms=100)

        voltages = result["voltages"]

        # Voltages should be in realistic range (-100mV to +50mV)
        assert np.all(voltages > -100)
        assert np.all(voltages < 50)

    def test_state_size_constant(self) -> None:
        """State dimensions don't change during simulation."""
        n_neurons = 15
        net = CA1Network(N=n_neurons, seed=42, dt=0.5)

        result1 = net.simulate(duration_ms=50)
        result2 = net.simulate(duration_ms=50)

        # Weight matrix size should stay constant
        assert result1["weights"].shape == (n_neurons, n_neurons)
        assert result2["weights"].shape == (n_neurons, n_neurons)

    def test_memory_state_copy_isolation(self) -> None:
        """Copied state is isolated from original."""
        weights = np.random.randn(5, 5)
        activations = np.random.randn(5)

        state = MemoryState(weights=weights, activations=activations)
        state_copy = state.copy()

        # Modify original
        state.weights[0, 0] = 999.0

        # Copy should be unaffected
        assert state_copy.weights[0, 0] != 999.0


class TestFiniteSafety:
    """Test 3: Finite safety - no NaN/Inf in outputs."""

    def test_simulation_outputs_finite(self) -> None:
        """All simulation outputs are finite."""
        net = CA1Network(N=20, seed=42, dt=0.5)
        result = net.simulate(duration_ms=100)

        for key, arr in result.items():
            assert np.all(np.isfinite(arr)), f"{key} contains non-finite values"

    def test_check_finite_raises_on_nan(self) -> None:
        """check_finite raises on NaN values."""
        arr_with_nan = np.array([1.0, 2.0, np.nan, 4.0])

        with pytest.raises(InvariantViolation, match="NaN"):
            check_finite(arr_with_nan, "test_array")

    def test_check_finite_raises_on_inf(self) -> None:
        """check_finite raises on Inf values."""
        arr_with_inf = np.array([1.0, np.inf, 3.0])

        with pytest.raises(InvariantViolation, match="Inf"):
            check_finite(arr_with_inf, "test_array")

    def test_check_finite_passes_on_valid(self) -> None:
        """check_finite passes for valid arrays."""
        valid_arr = np.array([1.0, 2.0, 3.0, -4.0])
        check_finite(valid_arr, "valid_array")  # Should not raise


class TestShapeSafety:
    """Test 4: Shape safety - incorrect dimensions give controlled errors."""

    def test_encode_input_rejects_3d_pattern(self) -> None:
        """EncodeInput rejects 3D patterns."""
        with pytest.raises(ValueError, match="1D or 2D"):
            EncodeInput(pattern=np.zeros((2, 3, 4)))

    def test_recall_query_rejects_2d_cue(self) -> None:
        """RecallQuery rejects 2D cues."""
        with pytest.raises(ValueError, match="1D"):
            RecallQuery(cue=np.zeros((3, 4)))

    def test_recall_result_rejects_2d_pattern(self) -> None:
        """RecallResult rejects 2D patterns."""
        with pytest.raises(ValueError, match="1D"):
            RecallResult(
                pattern=np.zeros((3, 4)),
                confidence=0.9,
                n_iterations_used=5,
                converged=True,
            )

    def test_update_input_rejects_mismatched_shapes(self) -> None:
        """UpdateInput rejects mismatched pre/post shapes."""
        with pytest.raises(ValueError, match="same shape"):
            UpdateInput(
                pre_activity=np.zeros(10),
                post_activity=np.zeros(20),
            )

    def test_check_shape_1d_rejects_2d(self) -> None:
        """check_shape_1d rejects 2D arrays."""
        with pytest.raises(InvariantViolation, match="1D"):
            check_shape_1d(np.zeros((3, 4)), expected_size=3)

    def test_check_shape_1d_rejects_wrong_size(self) -> None:
        """check_shape_1d rejects wrong size."""
        with pytest.raises(InvariantViolation, match="size"):
            check_shape_1d(np.zeros(5), expected_size=10)

    def test_check_square_matrix_rejects_rectangular(self) -> None:
        """check_square_matrix rejects rectangular matrices."""
        with pytest.raises(InvariantViolation, match="square"):
            check_square_matrix(np.zeros((3, 5)))

    def test_check_shape_2d_validates_correctly(self) -> None:
        """check_shape_2d works correctly."""
        from core.invariants import check_shape_2d

        valid = np.zeros((10, 10))
        check_shape_2d(valid, (10, 10))  # Should not raise

        with pytest.raises(InvariantViolation):
            check_shape_2d(np.zeros((5, 5)), (10, 10))


class TestMonotonicRecallSanity:
    """Test 5: Recall should at least match random baseline."""

    def test_recall_accuracy_above_random(self) -> None:
        """Recall accuracy should be above random baseline."""
        n = 100
        np.random.seed(42)

        # Create a stored pattern
        original = np.random.choice([-1, 1], size=n).astype(float)

        # Simulate recall (for now, use a noisy version as "recalled")
        noise_level = 0.1
        recalled = original + np.random.randn(n) * noise_level

        accuracy = recall_accuracy_proxy(original, recalled, method="cosine")

        # Random baseline for cosine similarity is ~0.5
        assert accuracy > 0.5, "Recall accuracy should be above random"

    def test_recall_accuracy_methods_consistent(self) -> None:
        """Different accuracy methods give reasonable results."""
        n = 50
        np.random.seed(42)

        original = np.random.randn(n)
        recalled = original * 0.9 + np.random.randn(n) * 0.1  # 90% signal

        cosine = recall_accuracy_proxy(original, recalled, method="cosine")
        mse = recall_accuracy_proxy(original, recalled, method="mse")

        # Both should indicate good recall
        assert cosine > 0.8
        assert mse > 0.7


class TestMetricsStability:
    """Test 6: Metrics return stable dictionary structure."""

    def test_compute_report_returns_all_keys(self) -> None:
        """compute_report returns all expected keys."""
        weights = np.random.randn(10, 10) * 0.1
        activations = np.random.randn(10)

        report = compute_report(weights, activations)

        assert validate_report(report), "Report missing expected keys"
        assert set(report.keys()) >= REPORT_KEYS

    def test_compute_report_no_exceptions(self) -> None:
        """compute_report doesn't raise on valid inputs."""
        # Various weight matrices
        test_cases = [
            np.zeros((5, 5)),
            np.eye(5),
            np.random.randn(5, 5),
            np.random.randn(10, 10) * 0.5,
        ]

        for weights in test_cases:
            activations = np.random.randn(weights.shape[0])
            report = compute_report(weights, activations)
            assert isinstance(report, dict)

    def test_memory_capacity_proxy_methods(self) -> None:
        """Different capacity methods work without error."""
        weights = np.random.randn(20, 20) * 0.1

        for method in ["rank", "eigenvalue", "sparsity"]:
            capacity = memory_capacity_proxy(weights, method=method)
            assert 0 <= capacity <= 1, f"Capacity out of bounds for {method}"

    def test_stability_metric_methods(self) -> None:
        """Different stability methods work without error."""
        weights = np.random.randn(15, 15) * 0.1

        for method in ["spectral", "condition", "norm"]:
            stability = stability_metric(weights, method=method)
            assert 0 <= stability <= 1, f"Stability out of bounds for {method}"

    def test_drift_metric_methods(self) -> None:
        """Different drift methods work without error."""
        before = np.random.randn(10, 10)
        after = before + np.random.randn(10, 10) * 0.1

        for method in ["absolute", "relative", "max"]:
            drift = drift_metric(before, after, method=method)
            assert drift >= 0, f"Drift should be non-negative for {method}"


class TestInvariantGuards:
    """Test invariant guard functions."""

    def test_check_bounded_passes_in_range(self) -> None:
        """check_bounded passes for values in range."""
        arr = np.array([0.5, 0.7, 0.3])
        check_bounded(arr, 0.0, 1.0)  # Should not raise

    def test_check_bounded_fails_out_of_range(self) -> None:
        """check_bounded fails for out of range values."""
        arr = np.array([0.5, 1.5, 0.3])
        with pytest.raises(InvariantViolation, match="must be in"):
            check_bounded(arr, 0.0, 1.0)

    def test_check_non_negative_passes(self) -> None:
        """check_non_negative passes for non-negative values."""
        arr = np.array([0.0, 1.0, 2.0])
        check_non_negative(arr)  # Should not raise

    def test_check_non_negative_fails(self) -> None:
        """check_non_negative fails for negative values."""
        arr = np.array([1.0, -0.1, 2.0])
        with pytest.raises(InvariantViolation, match="non-negative"):
            check_non_negative(arr)

    def test_check_probability_valid(self) -> None:
        """check_probability passes for valid probabilities."""
        probs = np.array([[0.3, 0.7], [0.5, 0.5]])
        check_probability(probs, axis=1)  # Should not raise

    def test_check_probability_invalid_sum(self) -> None:
        """check_probability fails for probabilities not summing to 1."""
        probs = np.array([0.3, 0.3])  # Sums to 0.6
        with pytest.raises(InvariantViolation, match="sum to 1"):
            check_probability(probs)

    def test_check_spectral_radius_stable(self) -> None:
        """check_spectral_radius passes for stable matrix."""
        weights = np.array([[0.1, 0.2], [0.2, 0.1]])  # Small values
        rho = check_spectral_radius(weights, max_radius=1.0)
        assert rho < 1.0

    def test_check_spectral_radius_unstable(self) -> None:
        """check_spectral_radius fails for unstable matrix."""
        weights = np.array([[2.0, 0.0], [0.0, 2.0]])  # Eigenvalues = 2
        with pytest.raises(InvariantViolation, match="spectral radius"):
            check_spectral_radius(weights, max_radius=1.0)

    def test_guards_can_be_disabled(self) -> None:
        """Guards can be disabled for production."""
        arr_with_nan = np.array([1.0, np.nan])

        # Should raise with guards enabled
        set_guards_enabled(True)
        with pytest.raises(InvariantViolation):
            check_finite(arr_with_nan)

        # Should not raise with guards disabled
        set_guards_enabled(False)
        check_finite(arr_with_nan)  # Should not raise

        # Re-enable for other tests
        set_guards_enabled(True)


class TestValidateMemoryState:
    """Test comprehensive state validation."""

    def test_validate_memory_state_all_valid(self) -> None:
        """validate_memory_state reports all valid for good state."""
        n = 10
        weights = np.random.randn(n, n) * 0.1
        activations = np.random.randn(n)

        results = validate_memory_state(weights, activations, weight_min=-1.0, weight_max=1.0)

        assert results["shape_valid"]
        assert results["finite_valid"]

    def test_validate_memory_state_detects_shape_error(self) -> None:
        """validate_memory_state detects shape mismatches."""
        weights = np.random.randn(10, 10)
        activations = np.random.randn(5)  # Wrong size

        results = validate_memory_state(weights, activations)

        assert not results["shape_valid"]

    def test_validate_memory_state_detects_nan(self) -> None:
        """validate_memory_state detects NaN values."""
        n = 10
        weights = np.random.randn(n, n)
        weights[0, 0] = np.nan
        activations = np.random.randn(n)

        results = validate_memory_state(weights, activations)

        assert not results["finite_valid"]


class TestContractDataclasses:
    """Test contract dataclass construction and validation."""

    def test_memory_state_construction(self) -> None:
        """MemoryState constructs correctly."""
        n = 10
        weights = np.random.randn(n, n)
        activations = np.random.randn(n)

        state = MemoryState(
            weights=weights,
            activations=activations,
            seed=42,
            phase=Phase.THETA,
        )

        assert state.n_neurons == n
        assert state.seed == 42
        assert state.phase == Phase.THETA

    def test_encode_input_valid(self) -> None:
        """EncodeInput accepts valid 1D pattern."""
        pattern = np.random.randn(50)
        encode = EncodeInput(pattern=pattern, strength=0.5)

        assert encode.strength == 0.5

    def test_encode_input_valid_2d(self) -> None:
        """EncodeInput accepts valid 2D pattern."""
        pattern = np.random.randn(10, 50)  # Time series
        encode = EncodeInput(pattern=pattern)

        assert encode.pattern.shape == (10, 50)

    def test_simulation_config_to_dict(self) -> None:
        """SimulationConfig serializes to dict."""
        config = SimulationConfig(n_neurons=100, seed=123)
        d = config.to_dict()

        assert d["n_neurons"] == 100
        assert d["seed"] == 123
        assert "debug_mode" in d
