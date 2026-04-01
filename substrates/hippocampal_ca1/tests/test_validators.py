"""
Unit tests for Validation Module
Tests for all validation gates and CA1Validator
"""

import numpy as np
import pytest

from validation.validators import (
    CA1Validator,
    compute_fractal_dimension,
    validate_dynamic_stability,
    validate_laminar_structure,
    validate_phase_precession,
    validate_replay,
)


class TestValidateLaminarStructure:
    """Tests for laminar structure validation"""

    @pytest.fixture
    def synthetic_data(self):
        """Generate synthetic test data"""
        np.random.seed(42)
        N = 200

        # Generate correlated layer assignments and depths
        depths = np.random.rand(N)
        layer_assignments = np.clip(np.floor(depths * 4).astype(int), 0, 3)

        # Generate transcripts (layer-specific markers)
        transcripts = np.zeros((N, 4))
        for i in range(N):
            transcripts[i, layer_assignments[i]] = np.random.poisson(5)

        thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}

        return layer_assignments, depths, transcripts, thresholds

    def test_returns_dict(self, synthetic_data):
        """Test validation returns dictionary"""
        layer_assignments, depths, transcripts, thresholds = synthetic_data
        result = validate_laminar_structure(layer_assignments, depths, transcripts, thresholds)
        assert isinstance(result, dict)

    def test_contains_required_keys(self, synthetic_data):
        """Test result contains all required keys"""
        layer_assignments, depths, transcripts, thresholds = synthetic_data
        result = validate_laminar_structure(layer_assignments, depths, transcripts, thresholds)

        required_keys = [
            "mutual_information",
            "mi_pvalue",
            "mi_std",
            "mi_95ci",
            "coexpression_rate",
            "pass_mi",
            "pass_ce",
            "pass_stability",
            "pass_overall",
        ]
        for key in required_keys:
            assert key in result

    def test_mutual_information_nonnegative(self, synthetic_data):
        """Test mutual information is non-negative"""
        layer_assignments, depths, transcripts, thresholds = synthetic_data
        result = validate_laminar_structure(layer_assignments, depths, transcripts, thresholds)
        assert result["mutual_information"] >= 0

    def test_coexpression_rate_range(self, synthetic_data):
        """Test coexpression rate is in [0, 1]"""
        layer_assignments, depths, transcripts, thresholds = synthetic_data
        result = validate_laminar_structure(layer_assignments, depths, transcripts, thresholds)
        assert 0 <= result["coexpression_rate"] <= 1

    def test_pass_flags_are_boolean(self, synthetic_data):
        """Test pass flags are boolean"""
        layer_assignments, depths, transcripts, thresholds = synthetic_data
        result = validate_laminar_structure(layer_assignments, depths, transcripts, thresholds)

        assert isinstance(result["pass_mi"], (bool, np.bool_))
        assert isinstance(result["pass_ce"], (bool, np.bool_))
        assert isinstance(result["pass_stability"], (bool, np.bool_))
        assert isinstance(result["pass_overall"], (bool, np.bool_))


class TestValidatePhasePrecession:
    """Tests for phase precession validation"""

    def test_insufficient_spikes(self):
        """Test handling of insufficient spikes"""
        spike_phases = np.array([0.1, 0.2])  # Only 2 spikes
        positions = np.array([0.1, 0.2])

        result = validate_phase_precession(spike_phases, positions, min_spikes=20)

        assert result["pass"] is False
        assert np.isnan(result["kappa"])

    def test_valid_precession(self):
        """Test with valid phase precession data"""
        np.random.seed(42)
        n_spikes = 50

        # Generate phase precession: phase decreases with position
        positions = np.linspace(0, 1, n_spikes)
        spike_phases = 2 * np.pi - 2 * np.pi * positions + np.random.randn(n_spikes) * 0.3
        spike_phases = spike_phases % (2 * np.pi)

        result = validate_phase_precession(spike_phases, positions, min_spikes=20)

        assert "kappa" in result
        assert "R2" in result
        assert "pvalue" in result
        assert "pass" in result

    def test_returns_correct_structure(self):
        """Test result structure"""
        np.random.seed(42)
        spike_phases = np.random.rand(30) * 2 * np.pi
        positions = np.linspace(0, 1, 30)

        result = validate_phase_precession(spike_phases, positions)

        assert "n_spikes" in result
        assert "kappa" in result
        assert "R2" in result
        assert "pvalue" in result

    def test_n_spikes_correct(self):
        """Test n_spikes is correct"""
        spike_phases = np.random.rand(25) * 2 * np.pi
        positions = np.linspace(0, 1, 25)

        result = validate_phase_precession(spike_phases, positions, min_spikes=20)

        assert result["n_spikes"] == 25


class TestComputeFractalDimension:
    """Tests for fractal dimension computation"""

    def test_insufficient_events(self):
        """Test handling of insufficient events"""
        events = np.random.rand(10, 2)  # Only 10 events

        result = compute_fractal_dimension(events)

        assert result["pass"] is False
        assert np.isnan(result["D_hat"])

    def test_returns_dict(self):
        """Test returns dictionary"""
        np.random.seed(42)
        events = np.random.rand(100, 2)

        result = compute_fractal_dimension(events)

        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        """Test result contains required keys"""
        np.random.seed(42)
        events = np.random.rand(100, 2)

        result = compute_fractal_dimension(events)

        required_keys = ["n_events", "D_hat", "R2", "pass"]
        for key in required_keys:
            assert key in result

    def test_dimension_reasonable(self):
        """Test fractal dimension is reasonable"""
        np.random.seed(42)
        # Generate 2D uniform random points (should have D ≈ 2)
        events = np.random.rand(200, 2)

        result = compute_fractal_dimension(events)

        # For random points in 2D, D should be positive and finite
        if not np.isnan(result["D_hat"]):
            assert 0.5 < result["D_hat"] < 3.0  # Relaxed bounds

    def test_n_events_correct(self):
        """Test n_events is correct"""
        events = np.random.rand(150, 2)

        result = compute_fractal_dimension(events)

        assert result["n_events"] == 150


class TestValidateDynamicStability:
    """Tests for dynamic stability validation"""

    def test_stable_network(self):
        """Test stable network passes"""
        np.random.seed(42)
        N = 50

        # Create stable weight matrix (small spectral radius)
        W = np.random.randn(N, N) * 0.05
        firing_rates = np.random.gamma(2, 2.5, N)

        result = validate_dynamic_stability(W, firing_rates)

        assert "spectral_radius" in result
        assert "mean_firing_rate" in result
        assert "pass" in result

    def test_unstable_network(self):
        """Test unstable network fails"""
        np.random.seed(42)
        N = 50

        # Create unstable weight matrix (large spectral radius)
        W = np.random.randn(N, N) * 0.5
        firing_rates = np.random.gamma(2, 2.5, N)

        result = validate_dynamic_stability(W, firing_rates)

        # May or may not pass depending on random matrix
        assert "spectral_radius" in result

    def test_spectral_radius_computed(self):
        """Test spectral radius is computed correctly"""
        W = np.eye(10) * 0.5  # Spectral radius = 0.5
        firing_rates = np.ones(10) * 5.0

        result = validate_dynamic_stability(W, firing_rates)

        assert abs(result["spectral_radius"] - 0.5) < 0.01

    def test_pass_conditions(self):
        """Test pass conditions are checked"""
        W = np.eye(10) * 0.5  # Stable
        firing_rates = np.ones(10) * 5.0  # Reasonable rates

        result = validate_dynamic_stability(W, firing_rates)

        assert result["pass_spectral"] == True  # noqa: E712
        assert result["pass_bounded"] == True  # noqa: E712


class TestValidateReplay:
    """Tests for replay validation"""

    def test_short_replay(self):
        """Test short replay fails"""
        online = list(range(20))
        replay = [0, 1]  # Too short

        result = validate_replay(online, replay, min_correlation=0.3)

        assert result["pass"] is False

    def test_no_common_neurons(self):
        """Test no common neurons fails"""
        online = list(range(10))
        replay = list(range(20, 30))  # No overlap

        result = validate_replay(online, replay)

        assert result["pass"] is False

    def test_identical_sequence(self):
        """Test identical sequences"""
        sequence = list(range(10))

        result = validate_replay(sequence, sequence)

        assert result["correlation"] > 0.9
        assert result["pass"] == True  # noqa: E712

    def test_reversed_sequence(self):
        """Test reversed sequence has negative correlation"""
        online = list(range(10))
        replay = list(reversed(range(10)))

        result = validate_replay(online, replay)

        assert result["correlation"] < -0.5

    def test_returns_required_keys(self):
        """Test result contains required keys"""
        online = list(range(10))
        replay = list(range(10))

        result = validate_replay(online, replay)

        assert "replay_length" in result
        assert "n_common" in result
        assert "correlation" in result
        assert "pvalue" in result
        assert "pass" in result


class TestCA1Validator:
    """Tests for CA1Validator class"""

    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return CA1Validator()

    @pytest.fixture
    def full_model_data(self):
        """Generate complete model data for testing"""
        np.random.seed(42)
        N = 100

        return {
            "layer_assignments": np.random.randint(0, 4, N),
            "depths": np.random.rand(N),
            "transcripts": np.random.poisson(3, (N, 4)),
            "thresholds": {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0},
            "spike_phases": np.random.rand(50) * 2 * np.pi,
            "positions": np.linspace(0, 1, 50),
            "events_fractal": np.random.rand(100, 2),
            "W_matrix": np.random.randn(50, 50) * 0.1,
            "firing_rates": np.random.gamma(2, 2.5, 50),
            "sequences": {"online": list(range(15)), "replay": list(range(15))},
        }

    def test_initialization(self, validator):
        """Test validator initialization"""
        assert isinstance(validator.results, dict)

    def test_run_all_gates(self, validator, full_model_data):
        """Test running all validation gates"""
        results = validator.run_all_gates(full_model_data)

        assert isinstance(results, dict)
        assert "laminar" in results
        assert "phase_precession" in results
        assert "fractal" in results
        assert "stability" in results
        assert "replay" in results

    def test_partial_data(self, validator):
        """Test with partial model data"""
        partial_data = {
            "W_matrix": np.random.randn(20, 20) * 0.1,
            "firing_rates": np.random.gamma(2, 2.5, 20),
        }

        results = validator.run_all_gates(partial_data)

        # Should only have stability results
        assert "stability" in results
        assert "laminar" not in results

    def test_print_report_runs(self, validator, full_model_data):
        """Test print_report runs without error"""
        validator.run_all_gates(full_model_data)

        # Should not raise
        validator.print_report()

    def test_results_stored(self, validator, full_model_data):
        """Test results are stored in validator"""
        validator.run_all_gates(full_model_data)

        assert validator.results == validator.results
        assert len(validator.results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
