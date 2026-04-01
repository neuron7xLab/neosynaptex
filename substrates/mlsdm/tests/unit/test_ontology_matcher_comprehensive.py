"""
Comprehensive tests for cognition/ontology_matcher.py.

Tests cover:
- OntologyMatcher initialization
- Cosine similarity matching
- Euclidean distance matching
- Edge cases (empty ontology, zero vectors, etc.)
- Serialization (to_dict)
"""

import numpy as np
import pytest

from mlsdm.cognition.ontology_matcher import OntologyMatcher


class TestOntologyMatcherInit:
    """Tests for OntologyMatcher initialization."""

    def test_valid_initialization(self):
        """Test valid initialization with numpy array."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        matcher = OntologyMatcher(vectors)
        assert matcher.dimension == 2
        assert len(matcher.labels) == 2

    def test_initialization_with_labels(self):
        """Test initialization with custom labels."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        labels = ["category_a", "category_b"]
        matcher = OntologyMatcher(vectors, labels=labels)
        assert matcher.labels == ["category_a", "category_b"]

    def test_initialization_default_labels(self):
        """Test default labels are integer indices."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
        matcher = OntologyMatcher(vectors)
        assert matcher.labels == [0, 1, 2]

    def test_invalid_not_numpy_array(self):
        """Test non-numpy array raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            OntologyMatcher([[1.0, 0.0], [0.0, 1.0]])
        assert "2D NumPy array" in str(exc_info.value)

    def test_invalid_1d_array(self):
        """Test 1D array raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            OntologyMatcher(np.array([1.0, 0.0, 0.0]))
        assert "2D NumPy array" in str(exc_info.value)

    def test_invalid_labels_length_mismatch(self):
        """Test mismatched labels length raises ValueError."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        labels = ["only_one"]
        with pytest.raises(ValueError) as exc_info:
            OntologyMatcher(vectors, labels=labels)
        assert "Length of labels must match" in str(exc_info.value)

    def test_dimension_stored_correctly(self):
        """Test dimension is stored correctly."""
        vectors = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        matcher = OntologyMatcher(vectors)
        assert matcher.dimension == 3


class TestCosineMatching:
    """Tests for cosine similarity matching."""

    def test_cosine_exact_match(self):
        """Test cosine matching with exact match."""
        vectors = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        matcher = OntologyMatcher(vectors, labels=["x", "y", "z"])

        label, score = matcher.match(np.array([1.0, 0.0, 0.0]), metric="cosine")
        assert label == "x"
        assert score == pytest.approx(1.0, rel=1e-6)

    def test_cosine_partial_match(self):
        """Test cosine matching with partial similarity."""
        vectors = np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
            ]
        )
        matcher = OntologyMatcher(vectors, labels=["a", "b"])

        # Vector [0.7, 0.7] is more similar to both equally
        label, score = matcher.match(np.array([1.0, 0.1]), metric="cosine")
        assert label == "a"  # Should match first one better
        assert score > 0.9

    def test_cosine_negative_similarity(self):
        """Test cosine matching with negative similarity."""
        vectors = np.array(
            [
                [1.0, 0.0],
                [-1.0, 0.0],
            ]
        )
        matcher = OntologyMatcher(vectors, labels=["pos", "neg"])

        label, score = matcher.match(np.array([-1.0, 0.0]), metric="cosine")
        assert label == "neg"
        assert score == pytest.approx(1.0, rel=1e-6)

    def test_cosine_default_metric(self):
        """Test that cosine is the default metric."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        matcher = OntologyMatcher(vectors)

        label1, score1 = matcher.match(np.array([1.0, 0.0]))
        label2, score2 = matcher.match(np.array([1.0, 0.0]), metric="cosine")
        assert label1 == label2
        assert score1 == score2


class TestEuclideanMatching:
    """Tests for euclidean distance matching."""

    def test_euclidean_exact_match(self):
        """Test euclidean matching with exact match."""
        vectors = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        matcher = OntologyMatcher(vectors, labels=["x", "y", "z"])

        label, score = matcher.match(np.array([1.0, 0.0, 0.0]), metric="euclidean")
        assert label == "x"
        # Score is negative distance, so exact match should be 0 (negative 0)
        assert score == pytest.approx(0.0, abs=1e-6)

    def test_euclidean_closest_match(self):
        """Test euclidean finds closest vector."""
        vectors = np.array(
            [
                [0.0, 0.0],
                [10.0, 10.0],
            ]
        )
        matcher = OntologyMatcher(vectors, labels=["origin", "far"])

        label, score = matcher.match(np.array([1.0, 1.0]), metric="euclidean")
        assert label == "origin"  # Closer to origin

    def test_euclidean_score_is_negative_distance(self):
        """Test euclidean score is negative distance."""
        vectors = np.array([[0.0, 0.0], [3.0, 4.0]])  # distance = 5 from [0,0] to [3,4]
        matcher = OntologyMatcher(vectors, labels=["a", "b"])

        # Query at [3, 4] should match "b" with distance 0
        label, score = matcher.match(np.array([3.0, 4.0]), metric="euclidean")
        assert label == "b"
        assert score == pytest.approx(0.0, abs=1e-6)

        # Query at [0, 0] should match "a" with distance 0
        label, score = matcher.match(np.array([0.0, 0.0]), metric="euclidean")
        assert label == "a"
        assert score == pytest.approx(0.0, abs=1e-6)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_ontology(self):
        """Test empty ontology returns None."""
        vectors = np.array([]).reshape(0, 3)  # Empty 2D array with dimension 3
        matcher = OntologyMatcher(vectors)

        label, score = matcher.match(np.array([1.0, 0.0, 0.0]))
        assert label is None
        assert score == 0.0

    def test_zero_query_vector(self):
        """Test zero query vector returns None (cosine)."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        matcher = OntologyMatcher(vectors)

        label, score = matcher.match(np.array([0.0, 0.0]), metric="cosine")
        assert label is None
        assert score == 0.0

    def test_zero_ontology_vectors(self):
        """Test all zero ontology vectors returns None (cosine)."""
        vectors = np.array([[0.0, 0.0], [0.0, 0.0]])
        matcher = OntologyMatcher(vectors, labels=["a", "b"])

        label, score = matcher.match(np.array([1.0, 0.0]), metric="cosine")
        assert label is None
        assert score == 0.0

    def test_single_ontology_vector(self):
        """Test with single ontology vector."""
        vectors = np.array([[1.0, 0.0]])
        matcher = OntologyMatcher(vectors, labels=["only"])

        label, score = matcher.match(np.array([0.5, 0.5]), metric="cosine")
        assert label == "only"

    def test_invalid_event_vector_type(self):
        """Test invalid event vector type raises ValueError."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        matcher = OntologyMatcher(vectors)

        with pytest.raises(ValueError) as exc_info:
            matcher.match([1.0, 0.0])  # List instead of numpy array
        assert "NumPy array" in str(exc_info.value)

    def test_invalid_event_vector_dimension(self):
        """Test wrong dimension event vector raises ValueError."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        matcher = OntologyMatcher(vectors)

        with pytest.raises(ValueError) as exc_info:
            matcher.match(np.array([1.0, 0.0, 0.0]))  # Wrong dimension
        assert "dimension 2" in str(exc_info.value)

    def test_invalid_metric(self):
        """Test invalid metric raises ValueError."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        matcher = OntologyMatcher(vectors)

        with pytest.raises(ValueError) as exc_info:
            matcher.match(np.array([1.0, 0.0]), metric="manhattan")
        assert "must be 'cosine' or 'euclidean'" in str(exc_info.value)


class TestToDict:
    """Tests for to_dict serialization."""

    def test_to_dict_basic(self):
        """Test to_dict returns correct structure."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        labels = ["a", "b"]
        matcher = OntologyMatcher(vectors, labels=labels)

        result = matcher.to_dict()
        assert "ontology_vectors" in result
        assert "labels" in result
        assert result["ontology_vectors"] == [[1.0, 0.0], [0.0, 1.0]]
        assert result["labels"] == ["a", "b"]

    def test_to_dict_with_integer_labels(self):
        """Test to_dict with default integer labels."""
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
        matcher = OntologyMatcher(vectors)

        result = matcher.to_dict()
        assert result["labels"] == [0, 1]

    def test_to_dict_converts_to_list(self):
        """Test that numpy arrays are converted to lists."""
        vectors = np.array([[1.5, 2.5], [3.5, 4.5]])
        matcher = OntologyMatcher(vectors)

        result = matcher.to_dict()
        assert isinstance(result["ontology_vectors"], list)
        assert isinstance(result["ontology_vectors"][0], list)


class TestMatchingAccuracy:
    """Tests for matching accuracy with various vector configurations."""

    def test_match_normalized_vectors(self):
        """Test matching with normalized vectors."""
        # Create unit vectors
        vectors = np.array(
            [
                [1.0, 0.0],
                [0.707107, 0.707107],  # 45 degrees
                [0.0, 1.0],
            ]
        )
        matcher = OntologyMatcher(vectors, labels=["0deg", "45deg", "90deg"])

        # Query close to 45 degrees
        query = np.array([0.6, 0.6])
        label, score = matcher.match(query, metric="cosine")
        assert label == "45deg"

    def test_match_high_dimensional(self):
        """Test matching in high dimensions."""
        np.random.seed(42)
        dim = 128
        n_vectors = 10

        # Create random unit vectors
        vectors = np.random.randn(n_vectors, dim)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

        matcher = OntologyMatcher(vectors)

        # Query should match itself best
        for i in range(n_vectors):
            label, score = matcher.match(vectors[i])
            assert label == i
            assert score == pytest.approx(1.0, rel=1e-5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
