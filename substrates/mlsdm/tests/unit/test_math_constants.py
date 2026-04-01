"""
Unit tests for math_constants module.

Tests the centralized mathematical constants and safe operations.
"""

import math

import numpy as np
import pytest

from mlsdm.utils.math_constants import (
    EPSILON_ABS,
    EPSILON_DIV,
    EPSILON_LOG,
    EPSILON_NORM,
    EPSILON_REL,
    batch_cosine_similarity,
    cosine_similarity,
    is_finite_array,
    is_finite_scalar,
    safe_divide,
    safe_entropy,
    safe_log,
    safe_log2,
    safe_norm,
    safe_normalize,
    validate_finite,
)


class TestEpsilonConstants:
    """Test that epsilon constants have expected values and properties."""

    def test_epsilon_constants_are_positive(self) -> None:
        """All epsilon constants should be positive."""
        assert EPSILON_NORM > 0
        assert EPSILON_DIV > 0
        assert EPSILON_LOG > 0
        assert EPSILON_REL > 0
        assert EPSILON_ABS > 0

    def test_epsilon_constants_are_small(self) -> None:
        """All epsilon constants should be small (less than 1e-5)."""
        assert EPSILON_NORM < 1e-5
        assert EPSILON_DIV < 1e-5
        assert EPSILON_LOG < 1e-5
        assert EPSILON_REL < 1e-5
        assert EPSILON_ABS < 1e-5

    def test_epsilon_log_is_smaller_than_norm(self) -> None:
        """EPSILON_LOG should be smaller than EPSILON_NORM for finer precision in log."""
        assert EPSILON_LOG < EPSILON_NORM


class TestIsFiniteScalar:
    """Test is_finite_scalar function."""

    def test_finite_float(self) -> None:
        """Finite floats should return True."""
        assert is_finite_scalar(1.0) is True
        assert is_finite_scalar(-1.0) is True
        assert is_finite_scalar(0.0) is True
        assert is_finite_scalar(1e-100) is True
        assert is_finite_scalar(1e100) is True

    def test_finite_int(self) -> None:
        """Finite integers should return True."""
        assert is_finite_scalar(1) is True
        assert is_finite_scalar(-1) is True
        assert is_finite_scalar(0) is True

    def test_nan_returns_false(self) -> None:
        """NaN should return False."""
        assert is_finite_scalar(float("nan")) is False

    def test_inf_returns_false(self) -> None:
        """Infinity should return False."""
        assert is_finite_scalar(float("inf")) is False
        assert is_finite_scalar(float("-inf")) is False

    def test_none_returns_false(self) -> None:
        """None should return False."""
        assert is_finite_scalar(None) is False

    def test_non_numeric_returns_false(self) -> None:
        """Non-numeric types should return False."""
        assert is_finite_scalar("1.0") is False  # type: ignore[arg-type]
        assert is_finite_scalar([1.0]) is False  # type: ignore[arg-type]


class TestIsFiniteArray:
    """Test is_finite_array function."""

    def test_finite_array(self) -> None:
        """Arrays with all finite values should return True."""
        assert is_finite_array(np.array([1.0, 2.0, 3.0])) is True
        assert is_finite_array(np.array([0.0])) is True
        assert is_finite_array(np.array([-1e100, 1e100])) is True

    def test_empty_array(self) -> None:
        """Empty arrays should return True (vacuously)."""
        assert is_finite_array(np.array([])) is True

    def test_nan_in_array(self) -> None:
        """Arrays with NaN should return False."""
        assert is_finite_array(np.array([1.0, np.nan, 3.0])) is False

    def test_inf_in_array(self) -> None:
        """Arrays with infinity should return False."""
        assert is_finite_array(np.array([1.0, np.inf])) is False
        assert is_finite_array(np.array([1.0, -np.inf])) is False

    def test_non_array_returns_false(self) -> None:
        """Non-array types should return False."""
        assert is_finite_array([1.0, 2.0]) is False  # type: ignore[arg-type]
        assert is_finite_array(1.0) is False  # type: ignore[arg-type]


class TestValidateFinite:
    """Test validate_finite function."""

    def test_valid_float(self) -> None:
        """Valid floats should be returned as-is."""
        assert validate_finite(1.0, "x") == 1.0
        assert validate_finite(0.0, "x") == 0.0

    def test_valid_array(self) -> None:
        """Valid arrays should be returned as-is."""
        arr = np.array([1.0, 2.0, 3.0])
        result = validate_finite(arr, "x")
        np.testing.assert_array_equal(result, arr)

    def test_nan_with_default(self) -> None:
        """NaN with default should return default."""
        assert validate_finite(float("nan"), "x", default=0.0) == 0.0

    def test_nan_without_default_raises(self) -> None:
        """NaN without default should raise ValueError."""
        with pytest.raises(ValueError, match="must be finite"):
            validate_finite(float("nan"), "x")

    def test_inf_without_default_raises(self) -> None:
        """Infinity without default should raise ValueError."""
        with pytest.raises(ValueError, match="must be finite"):
            validate_finite(float("inf"), "x")


class TestSafeDivide:
    """Test safe_divide function."""

    def test_normal_division_scalar(self) -> None:
        """Normal division should work as expected."""
        assert safe_divide(4.0, 2.0) == 2.0
        assert safe_divide(1.0, 4.0) == 0.25

    def test_division_by_zero_scalar(self) -> None:
        """Division by zero should return large value."""
        result = safe_divide(1.0, 0.0)
        assert result > 1e8  # Should be approximately 1/epsilon

    def test_division_by_small_value_scalar(self) -> None:
        """Division by very small value uses epsilon."""
        result = safe_divide(1.0, 1e-15)
        assert result > 1e8  # Should use epsilon instead

    def test_normal_division_array(self) -> None:
        """Normal array division should work."""
        num = np.array([4.0, 6.0])
        denom = np.array([2.0, 3.0])
        result = safe_divide(num, denom)
        np.testing.assert_array_almost_equal(result, np.array([2.0, 2.0]))

    def test_division_by_zero_array(self) -> None:
        """Array division by zero should be handled."""
        num = np.array([1.0, 2.0])
        denom = np.array([0.0, 1.0])
        result = safe_divide(num, denom)
        assert result[0] > 1e8  # First element divided by epsilon
        assert result[1] == 2.0  # Second element normal


class TestSafeNorm:
    """Test safe_norm function for overflow-safe L2 norm computation."""

    def test_normal_vector(self) -> None:
        """Normal vectors should compute correctly."""
        vec = np.array([3.0, 4.0])
        result = safe_norm(vec)
        assert abs(result - 5.0) < 1e-10

    def test_zero_vector(self) -> None:
        """Zero vector should return 0."""
        vec = np.array([0.0, 0.0, 0.0])
        result = safe_norm(vec)
        assert result == 0.0

    def test_unit_vector(self) -> None:
        """Unit vector should return 1."""
        vec = np.array([1.0, 0.0, 0.0])
        result = safe_norm(vec)
        assert abs(result - 1.0) < 1e-10

    def test_extreme_large_magnitude(self) -> None:
        """Extremely large vectors should not overflow."""
        vec = np.array([1e30, 1e30])
        result = safe_norm(vec)
        # Expected: sqrt(2) * 1e30 ≈ 1.414e30
        expected = np.sqrt(2.0) * 1e30
        assert np.isfinite(result)
        assert abs(result - expected) / expected < 1e-6

    def test_extreme_small_magnitude(self) -> None:
        """Extremely small vectors should work correctly."""
        vec = np.array([1e-30, 1e-30])
        result = safe_norm(vec)
        expected = np.sqrt(2.0) * 1e-30
        assert np.isfinite(result)
        assert abs(result - expected) / expected < 1e-6

    def test_mixed_magnitude(self) -> None:
        """Mixed magnitude vectors should work correctly."""
        vec = np.array([1e20, 1e-20])
        result = safe_norm(vec)
        # The large component dominates
        assert np.isfinite(result)
        assert abs(result - 1e20) / 1e20 < 1e-6

    def test_negative_values(self) -> None:
        """Negative values should work correctly."""
        vec = np.array([-3.0, -4.0])
        result = safe_norm(vec)
        assert abs(result - 5.0) < 1e-10

    def test_single_element(self) -> None:
        """Single element vectors should work."""
        vec = np.array([5.0])
        result = safe_norm(vec)
        assert abs(result - 5.0) < 1e-10

    def test_large_dimension(self) -> None:
        """High-dimensional vectors should work."""
        dim = 1000
        vec = np.ones(dim) * 1e20
        result = safe_norm(vec)
        expected = np.sqrt(dim) * 1e20
        assert np.isfinite(result)
        assert abs(result - expected) / expected < 1e-6

    def test_inf_vector(self) -> None:
        """Vector containing inf should return inf."""
        vec = np.array([np.inf, 1.0])
        result = safe_norm(vec)
        assert result == float("inf")

    def test_consistency_with_numpy(self) -> None:
        """For normal values, should match np.linalg.norm closely."""
        np.random.seed(42)
        for _ in range(10):
            vec = np.random.randn(100)
            result = safe_norm(vec)
            expected = np.linalg.norm(vec)
            assert abs(result - expected) / max(expected, 1e-10) < 1e-10


class TestSafeNormalize:
    """Test safe_normalize function."""

    def test_normal_vector(self) -> None:
        """Normal vectors should be normalized to unit length."""
        vec = np.array([3.0, 4.0])
        result = safe_normalize(vec)
        np.testing.assert_array_almost_equal(result, np.array([0.6, 0.8]))
        assert abs(np.linalg.norm(result) - 1.0) < 1e-10

    def test_zero_vector(self) -> None:
        """Zero vectors should be returned as-is."""
        vec = np.array([0.0, 0.0])
        result = safe_normalize(vec)
        np.testing.assert_array_equal(result, vec)

    def test_very_small_vector(self) -> None:
        """Very small vectors should be returned as-is."""
        vec = np.array([1e-15, 1e-15])
        result = safe_normalize(vec)
        np.testing.assert_array_equal(result, vec)

    def test_negative_vector(self) -> None:
        """Negative vectors should work correctly."""
        vec = np.array([-3.0, 4.0])
        result = safe_normalize(vec)
        np.testing.assert_array_almost_equal(result, np.array([-0.6, 0.8]))


class TestSafeLog:
    """Test safe_log function."""

    def test_normal_value(self) -> None:
        """Normal values should work."""
        assert abs(safe_log(1.0) - 0.0) < 1e-10
        assert abs(safe_log(math.e) - 1.0) < 1e-10

    def test_zero_value(self) -> None:
        """Zero should not cause error."""
        result = safe_log(0.0)
        assert math.isfinite(result)
        assert result < 0  # log of small number is negative

    def test_array_values(self) -> None:
        """Array values should work."""
        arr = np.array([1.0, math.e])
        result = safe_log(arr)
        assert abs(result[0] - 0.0) < 1e-10
        assert abs(result[1] - 1.0) < 1e-10


class TestSafeLog2:
    """Test safe_log2 function."""

    def test_normal_value(self) -> None:
        """Normal values should work."""
        assert abs(safe_log2(1.0) - 0.0) < 1e-10
        assert abs(safe_log2(2.0) - 1.0) < 1e-10
        assert abs(safe_log2(4.0) - 2.0) < 1e-10

    def test_zero_value(self) -> None:
        """Zero should not cause error."""
        result = safe_log2(0.0)
        assert math.isfinite(result)
        assert result < 0


class TestSafeEntropy:
    """Test safe_entropy function."""

    def test_empty_array(self) -> None:
        """Empty array should return 0."""
        assert safe_entropy(np.array([])) == 0.0

    def test_uniform_distribution(self) -> None:
        """Uniform distribution should have maximum entropy."""
        # For n equal elements, entropy should be log2(n)
        vec = np.array([1.0, 1.0])
        result = safe_entropy(vec)
        assert abs(result - 1.0) < 0.1  # log2(2) = 1

    def test_varied_values(self) -> None:
        """Different values should produce different entropy than uniform."""
        uniform = np.array([1.0, 1.0, 1.0])
        varied = np.array([1.0, 2.0, 3.0])
        uniform_entropy = safe_entropy(uniform)
        varied_entropy = safe_entropy(varied)
        # Both should be positive and finite
        assert uniform_entropy > 0
        assert varied_entropy > 0
        # They should be different (non-uniform has lower entropy)
        assert abs(uniform_entropy - varied_entropy) > 0.01

    def test_returns_finite(self) -> None:
        """Entropy should always return finite values."""
        test_cases = [
            np.array([0.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
            np.array([1e-10, 1e-10]),
            np.array([1e10, 1e10]),
        ]
        for vec in test_cases:
            result = safe_entropy(vec)
            assert math.isfinite(result), f"Non-finite result for {vec}"


class TestCosineSimilarity:
    """Test cosine_similarity function."""

    def test_identical_vectors(self) -> None:
        """Identical vectors should have similarity 1."""
        vec = np.array([1.0, 0.0, 0.0])
        assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-10

    def test_orthogonal_vectors(self) -> None:
        """Orthogonal vectors should have similarity 0."""
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        assert abs(cosine_similarity(v1, v2)) < 1e-10

    def test_opposite_vectors(self) -> None:
        """Opposite vectors should have similarity -1."""
        v1 = np.array([1.0, 0.0])
        v2 = np.array([-1.0, 0.0])
        assert abs(cosine_similarity(v1, v2) - (-1.0)) < 1e-10

    def test_zero_vector_returns_zero(self) -> None:
        """Zero vectors should return 0 similarity."""
        v1 = np.array([0.0, 0.0])
        v2 = np.array([1.0, 0.0])
        assert cosine_similarity(v1, v2) == 0.0
        assert cosine_similarity(v2, v1) == 0.0


class TestBatchCosineSimilarity:
    """Test batch_cosine_similarity function."""

    def test_basic_batch(self) -> None:
        """Basic batch similarity should work."""
        query = np.array([1.0, 0.0])
        vectors = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])
        result = batch_cosine_similarity(query, vectors)
        np.testing.assert_array_almost_equal(result, np.array([1.0, 0.0, -1.0]))

    def test_zero_query(self) -> None:
        """Zero query should return all zeros."""
        query = np.array([0.0, 0.0])
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        result = batch_cosine_similarity(query, vectors)
        np.testing.assert_array_equal(result, np.array([0.0, 0.0]))

    def test_zero_vector_in_batch(self) -> None:
        """Zero vectors in batch should have 0 similarity."""
        query = np.array([1.0, 0.0])
        vectors = np.array([[1.0, 0.0], [0.0, 0.0]])
        result = batch_cosine_similarity(query, vectors)
        assert result[0] == pytest.approx(1.0)
        assert result[1] == 0.0
