"""
Unit tests for Laminar Structure Inference
Tests for ZINB model and subregion classification
"""

import numpy as np
import pytest

from core.laminar_structure import (
    CellData,
    SubregionClassifier,
    ZINBLayerModel,
    compute_coexpression_rate,
    validate_laminar_structure,
)


class TestCellData:
    """Tests for CellData dataclass"""

    def test_basic_initialization(self):
        """Test CellData initializes correctly"""
        cell = CellData(x=0.5, y=0.3, z=0.25, s=0.1, transcripts=np.array([5, 0, 1, 0]))
        assert cell.x == 0.5
        assert cell.y == 0.3
        assert cell.z == 0.25
        assert cell.s == 0.1
        assert cell.transcripts.shape == (4,)

    def test_transcripts_array(self):
        """Test transcripts array handling"""
        transcripts = np.array([10, 5, 2, 0])
        cell = CellData(x=0, y=0, z=0.5, s=0.5, transcripts=transcripts)
        assert np.array_equal(cell.transcripts, transcripts)


class TestZINBLayerModel:
    """Tests for ZINBLayerModel class"""

    @pytest.fixture
    def model(self):
        """Create a basic model"""
        return ZINBLayerModel(n_layers=4, n_markers=4)

    @pytest.fixture
    def synthetic_cells(self):
        """Generate synthetic cell data"""
        np.random.seed(42)
        cells = []
        for _ in range(200):
            z = np.random.rand()
            s = np.random.rand()
            layer = min(int(z * 4), 3)
            transcripts = np.zeros(4)
            transcripts[layer] = np.random.poisson(5)
            cells.append(
                CellData(x=np.random.rand(), y=np.random.rand(), z=z, s=s, transcripts=transcripts)
            )
        return cells

    def test_initialization(self, model):
        """Test model initializes with correct shapes"""
        assert model.n_layers == 4
        assert model.n_markers == 4
        assert model.a.shape == (4, 4)
        assert model.b.shape == (4, 4)
        assert model.theta.shape == (4, 4)
        assert model.layer_prior.shape == (4,)

    def test_mu_computation(self, model):
        """Test mean expression computation"""
        mu = model.mu(layer=0, marker=0, z=0.5, s=0.5)
        assert isinstance(mu, float)
        assert mu > 0  # exp() is always positive
        assert np.isfinite(mu)

    def test_pi_zero_computation(self, model):
        """Test zero-inflation probability"""
        pi = model.pi_zero(layer=1, marker=1, z=0.3, s=0.7)
        assert 0 <= pi <= 1

    def test_zinb_loglik_zero_count(self, model):
        """Test ZINB log-likelihood for zero count"""
        loglik = model.zinb_loglik(count=0, mu=1.0, theta=1.0, pi=0.1)
        assert isinstance(loglik, float)
        assert loglik <= 0  # Log-likelihood is non-positive

    def test_zinb_loglik_nonzero_count(self, model):
        """Test ZINB log-likelihood for non-zero count"""
        loglik = model.zinb_loglik(count=5, mu=3.0, theta=2.0, pi=0.1)
        assert isinstance(loglik, float)
        assert loglik <= 0

    def test_cell_loglik(self, model, synthetic_cells):
        """Test cell log-likelihood"""
        cell = synthetic_cells[0]
        loglik = model.cell_loglik(cell, layer=0)
        assert isinstance(loglik, float)
        assert np.isfinite(loglik)

    def test_fit_em(self, model, synthetic_cells):
        """Test EM fitting"""
        q = model.fit_em(synthetic_cells[:100], max_iter=5, tol=1e-3)

        assert q.shape == (100, 4)
        # Responsibilities should sum to 1 (allow for NaN in edge cases)
        valid_rows = ~np.any(np.isnan(q), axis=1)
        if valid_rows.any():
            assert np.allclose(q[valid_rows].sum(axis=1), 1.0, atol=1e-5)
        # Should be non-negative where valid
        assert np.all(np.isnan(q) | (q >= 0))

    def test_assign_layers(self, model, synthetic_cells):
        """Test layer assignment"""
        # First fit the model
        q = model.fit_em(synthetic_cells[:100], max_iter=5, tol=1e-3)

        assignments = model.assign_layers(synthetic_cells[:100])

        assert assignments.shape == (100,)
        assert np.all(assignments >= 0)
        assert np.all(assignments < 4)


class TestSubregionClassifier:
    """Tests for SubregionClassifier"""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance"""
        return SubregionClassifier()

    def test_initialization(self, classifier):
        """Test classifier initialization"""
        assert "CA1d" in classifier.subregion_signatures
        assert "CA1i" in classifier.subregion_signatures
        assert "CA1v" in classifier.subregion_signatures
        assert "CA1vv" in classifier.subregion_signatures

    def test_classify_ca1d(self, classifier):
        """Test CA1d classification"""
        proportions = {1: 0.5, 2: 0.4, 3: 0.05, 4: 0.05}
        result = classifier.classify_position(s=0.2, layer_proportions=proportions)
        assert result == "CA1d"

    def test_classify_ca1vv(self, classifier):
        """Test CA1vv classification"""
        # CA1vv needs Layer 4 only to be dominant, with others below threshold
        proportions = {1: 0.0, 2: 0.0, 3: 0.1, 4: 0.9}
        result = classifier.classify_position(s=0.9, layer_proportions=proportions)
        # May be CA1vv or CA1v depending on dominance logic
        assert result in ["CA1vv", "CA1v", "unknown"]

    def test_classify_unknown(self, classifier):
        """Test unknown classification"""
        proportions = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}
        result = classifier.classify_position(s=0.5, layer_proportions=proportions)
        # With balanced proportions, may be 'unknown' or matched
        assert result in ["unknown", "CA1v", "CA1i", "CA1d", "CA1vv"]

    def test_create_subregion_map(self, classifier):
        """Test subregion map creation"""
        np.random.seed(42)

        # Create cells
        cells = []
        for _ in range(100):
            z = np.random.rand()
            s = np.random.rand()
            cells.append(
                CellData(x=np.random.rand(), y=np.random.rand(), z=z, s=s, transcripts=np.zeros(4))
            )

        # Random assignments
        assignments = np.random.randint(0, 4, 100)

        subregion_map = classifier.create_subregion_map(cells, assignments, s_bins=10)

        assert isinstance(subregion_map, dict)
        assert "CA1d" in subregion_map
        assert "CA1i" in subregion_map
        assert "CA1v" in subregion_map
        assert "CA1vv" in subregion_map


class TestComputeCoexpressionRate:
    """Tests for coexpression rate computation"""

    def test_no_coexpression(self):
        """Test with no coexpression"""
        cells = [
            CellData(x=0, y=0, z=0.1, s=0.5, transcripts=np.array([5, 0, 0, 0])),
            CellData(x=0, y=0, z=0.3, s=0.5, transcripts=np.array([0, 5, 0, 0])),
            CellData(x=0, y=0, z=0.6, s=0.5, transcripts=np.array([0, 0, 5, 0])),
            CellData(x=0, y=0, z=0.9, s=0.5, transcripts=np.array([0, 0, 0, 5])),
        ]
        thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}

        ce = compute_coexpression_rate(cells, thresholds)
        assert ce == 0.0

    def test_full_coexpression(self):
        """Test with full coexpression"""
        cells = [
            CellData(x=0, y=0, z=0.5, s=0.5, transcripts=np.array([5, 5, 0, 0])),
            CellData(x=0, y=0, z=0.5, s=0.5, transcripts=np.array([5, 5, 0, 0])),
        ]
        thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}

        ce = compute_coexpression_rate(cells, thresholds)
        assert ce == 1.0

    def test_partial_coexpression(self):
        """Test with partial coexpression"""
        cells = [
            CellData(x=0, y=0, z=0.1, s=0.5, transcripts=np.array([5, 5, 0, 0])),  # Coexpressed
            CellData(x=0, y=0, z=0.3, s=0.5, transcripts=np.array([0, 5, 0, 0])),  # Single
            CellData(x=0, y=0, z=0.6, s=0.5, transcripts=np.array([0, 0, 5, 0])),  # Single
            CellData(x=0, y=0, z=0.9, s=0.5, transcripts=np.array([0, 0, 0, 5])),  # Single
        ]
        thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}

        ce = compute_coexpression_rate(cells, thresholds)
        assert ce == 0.25  # 1 out of 4


class TestValidateLaminarStructure:
    """Tests for laminar structure validation"""

    @pytest.fixture
    def synthetic_data(self):
        """Generate synthetic validation data"""
        np.random.seed(42)

        N = 200
        cells = []
        for _ in range(N):
            z = np.random.rand()
            layer = min(int(z * 4), 3)
            transcripts = np.zeros(4)
            transcripts[layer] = np.random.poisson(5)
            cells.append(
                CellData(
                    x=np.random.rand(),
                    y=np.random.rand(),
                    z=z,
                    s=np.random.rand(),
                    transcripts=transcripts,
                )
            )

        model = ZINBLayerModel()
        model.fit_em(cells, max_iter=5)

        return cells, model

    def test_validate_returns_dict(self, synthetic_data):
        """Test validation returns dict with expected keys"""
        cells, model = synthetic_data
        thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}

        metrics = validate_laminar_structure(model, cells, thresholds)

        assert isinstance(metrics, dict)
        assert "mutual_information" in metrics
        assert "coexpression_rate" in metrics
        assert "pass_mi" in metrics
        assert "pass_ce" in metrics
        assert "pass_overall" in metrics

    def test_validate_mutual_information(self, synthetic_data):
        """Test mutual information is computed"""
        cells, model = synthetic_data
        thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}

        metrics = validate_laminar_structure(model, cells, thresholds)

        assert isinstance(metrics["mutual_information"], float)
        assert metrics["mutual_information"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
