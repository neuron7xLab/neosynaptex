"""
Unit Tests for Moral Filter

Tests moral threshold filtering and adaptation.
"""

import pytest

from mlsdm.cognition.moral_filter import MoralFilter


class TestMoralFilterInitialization:
    """Test moral filter initialization."""

    def test_default_initialization(self):
        """Test filter can be initialized with defaults."""
        filter = MoralFilter()
        assert filter.threshold == 0.5
        assert filter.adapt_rate == 0.05
        assert filter.min_threshold == 0.3
        assert filter.max_threshold == 0.9

    def test_custom_initialization(self):
        """Test filter can be initialized with custom values."""
        filter = MoralFilter(threshold=0.6, adapt_rate=0.1, min_threshold=0.2, max_threshold=0.95)
        assert filter.threshold == 0.6
        assert filter.adapt_rate == 0.1
        assert filter.min_threshold == 0.2
        assert filter.max_threshold == 0.95

    def test_invalid_threshold(self):
        """Test initialization rejects invalid threshold."""
        with pytest.raises(ValueError):
            MoralFilter(threshold=1.5)

        with pytest.raises(ValueError):
            MoralFilter(threshold=-0.1)

    def test_invalid_adapt_rate(self):
        """Test initialization rejects invalid adapt rate."""
        with pytest.raises(ValueError):
            MoralFilter(adapt_rate=1.5)

        with pytest.raises(ValueError):
            MoralFilter(adapt_rate=-0.1)


class TestMoralFilterEvaluate:
    """Test moral filter evaluation."""

    def test_evaluate_above_threshold(self):
        """Test evaluation accepts value above threshold."""
        filter = MoralFilter(threshold=0.5)
        assert filter.evaluate(0.6) is True
        assert filter.evaluate(0.9) is True

    def test_evaluate_below_threshold(self):
        """Test evaluation rejects value below threshold."""
        filter = MoralFilter(threshold=0.5)
        assert filter.evaluate(0.4) is False
        assert filter.evaluate(0.1) is False

    def test_evaluate_at_threshold(self):
        """Test evaluation at exact threshold."""
        filter = MoralFilter(threshold=0.5)
        assert filter.evaluate(0.5) is True

    def test_evaluate_invalid_value(self):
        """Test evaluation rejects invalid moral value."""
        filter = MoralFilter()

        with pytest.raises(ValueError):
            filter.evaluate(1.5)

        with pytest.raises(ValueError):
            filter.evaluate(-0.1)


class TestMoralFilterAdapt:
    """Test moral filter adaptation."""

    def test_adapt_decrease_threshold(self):
        """Test threshold decreases with low accept rate."""
        filter = MoralFilter(threshold=0.5, adapt_rate=0.1)
        initial_threshold = filter.threshold

        filter.adapt(accept_rate=0.3)

        assert filter.threshold < initial_threshold
        assert filter.threshold == 0.4  # 0.5 - 0.1

    def test_adapt_increase_threshold(self):
        """Test threshold increases with high accept rate."""
        filter = MoralFilter(threshold=0.5, adapt_rate=0.1)
        initial_threshold = filter.threshold

        filter.adapt(accept_rate=0.7)

        assert filter.threshold > initial_threshold
        assert filter.threshold == 0.6  # 0.5 + 0.1

    def test_adapt_at_boundary(self):
        """Test threshold adaptation at 0.5 boundary."""
        filter = MoralFilter(threshold=0.5, adapt_rate=0.1)

        # Exactly 0.5 should increase (>= 0.5 condition)
        filter.adapt(accept_rate=0.5)
        assert filter.threshold == 0.6

    def test_adapt_respects_min_threshold(self):
        """Test threshold doesn't go below minimum."""
        filter = MoralFilter(threshold=0.3, adapt_rate=0.1, min_threshold=0.3)

        filter.adapt(accept_rate=0.1)

        assert filter.threshold == 0.3  # Should stay at minimum

    def test_adapt_respects_max_threshold(self):
        """Test threshold doesn't go above maximum."""
        filter = MoralFilter(threshold=0.9, adapt_rate=0.1, max_threshold=0.9)

        filter.adapt(accept_rate=0.9)

        assert filter.threshold == 0.9  # Should stay at maximum

    def test_adapt_invalid_accept_rate(self):
        """Test adapt rejects invalid accept rate."""
        filter = MoralFilter()

        with pytest.raises(ValueError):
            filter.adapt(1.5)

        with pytest.raises(ValueError):
            filter.adapt(-0.1)


class TestMoralFilterToDict:
    """Test moral filter serialization."""

    def test_to_dict(self):
        """Test filter can be serialized to dict."""
        filter = MoralFilter(threshold=0.6, adapt_rate=0.1, min_threshold=0.2, max_threshold=0.95)

        data = filter.to_dict()

        assert isinstance(data, dict)
        assert data["threshold"] == 0.6
        assert data["adapt_rate"] == 0.1
        assert data["min_threshold"] == 0.2
        assert data["max_threshold"] == 0.95

    def test_to_dict_default_values(self):
        """Test to_dict with default initialization."""
        filter = MoralFilter()
        data = filter.to_dict()

        assert data["threshold"] == 0.5
        assert data["adapt_rate"] == 0.05
        assert data["min_threshold"] == 0.3
        assert data["max_threshold"] == 0.9


class TestMoralFilterIntegration:
    """Test moral filter integration scenarios."""

    def test_adaptive_sequence(self):
        """Test threshold adapts over multiple evaluations."""
        filter = MoralFilter(threshold=0.5, adapt_rate=0.1)

        # Simulate low accept rate scenario
        filter.adapt(0.2)
        assert pytest.approx(filter.threshold) == 0.4

        filter.adapt(0.3)
        assert pytest.approx(filter.threshold) == 0.3

        # Now simulate high accept rate
        filter.adapt(0.8)
        assert pytest.approx(filter.threshold) == 0.4

        filter.adapt(0.9)
        assert pytest.approx(filter.threshold) == 0.5

    def test_convergence_to_limits(self):
        """Test filter converges to limits with extreme adapt rates."""
        filter = MoralFilter(threshold=0.5, adapt_rate=0.2, min_threshold=0.3, max_threshold=0.9)

        # Push to minimum
        for _ in range(5):
            filter.adapt(0.1)

        assert filter.threshold == 0.3

        # Push to maximum
        for _ in range(10):
            filter.adapt(0.9)

        assert filter.threshold == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
