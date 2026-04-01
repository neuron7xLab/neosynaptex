"""Tests for FractalPELMGPU experimental memory module.

These tests run on CPU without requiring GPU hardware.
They validate the experimental GPU/CPU backend for phase-aware retrieval.

Requires PyTorch (torch). Tests are skipped if torch is not installed.
"""

import numpy as np
import pytest

# Skip all tests in this module if torch is not available
pytest.importorskip("torch")

from mlsdm.memory.experimental import FractalPELMGPU


class TestFractalPELMGPUInitialization:
    """Test FractalPELMGPU initialization and validation."""

    def test_initialization_defaults(self) -> None:
        """Test initialization with default parameters."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")
        assert memory.dimension == 16
        assert memory.capacity == 100
        assert memory.size == 0
        assert "cpu" in memory.device

    def test_initialization_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        memory = FractalPELMGPU(
            dimension=32,
            capacity=500,
            device="cpu",
            use_amp=False,
            fractal_weight=0.5,
        )
        assert memory.dimension == 32
        assert memory.capacity == 500
        assert memory.fractal_weight == 0.5

    def test_invalid_dimension_raises_error(self) -> None:
        """Test that invalid dimension raises ValueError."""
        with pytest.raises(ValueError, match="dimension must be positive"):
            FractalPELMGPU(dimension=0, capacity=100, device="cpu")

        with pytest.raises(ValueError, match="dimension must be positive"):
            FractalPELMGPU(dimension=-1, capacity=100, device="cpu")

    def test_invalid_capacity_raises_error(self) -> None:
        """Test that invalid capacity raises ValueError."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            FractalPELMGPU(dimension=16, capacity=0, device="cpu")

        with pytest.raises(ValueError, match="capacity must be positive"):
            FractalPELMGPU(dimension=16, capacity=-10, device="cpu")


class TestFractalPELMGPUBatchEntangle:
    """Test batch_entangle method."""

    def test_basic_batch_entangle(self) -> None:
        """Test basic batch entangle operation."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        vectors = np.random.randn(10, 16).astype(np.float32)
        phases = np.random.rand(10).astype(np.float32)

        memory.batch_entangle(vectors, phases)

        assert memory.size == 10

    def test_entangle_with_metadata(self) -> None:
        """Test batch entangle with metadata."""
        memory = FractalPELMGPU(dimension=8, capacity=50, device="cpu")

        vectors = np.random.randn(5, 8).astype(np.float32)
        phases = np.random.rand(5).astype(np.float32)
        metadatas = [{"id": i, "label": f"item_{i}"} for i in range(5)]

        memory.batch_entangle(vectors, phases, metadatas)

        assert memory.size == 5

    def test_capacity_overflow_raises_error(self) -> None:
        """Test that exceeding capacity raises RuntimeError."""
        memory = FractalPELMGPU(dimension=8, capacity=10, device="cpu")

        # First batch of 6 should succeed
        vectors1 = np.random.randn(6, 8).astype(np.float32)
        phases1 = np.random.rand(6).astype(np.float32)
        memory.batch_entangle(vectors1, phases1)
        assert memory.size == 6

        # Second batch of 6 should fail (6 + 6 > 10)
        vectors2 = np.random.randn(6, 8).astype(np.float32)
        phases2 = np.random.rand(6).astype(np.float32)

        with pytest.raises(RuntimeError, match="would exceed capacity"):
            memory.batch_entangle(vectors2, phases2)

    def test_dimension_mismatch_raises_error(self) -> None:
        """Test that dimension mismatch raises ValueError."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        vectors = np.random.randn(5, 32).astype(np.float32)  # Wrong dimension
        phases = np.random.rand(5).astype(np.float32)

        with pytest.raises(ValueError, match="dimension mismatch"):
            memory.batch_entangle(vectors, phases)

    def test_batch_size_mismatch_raises_error(self) -> None:
        """Test that batch size mismatch raises ValueError."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu")

        vectors = np.random.randn(10, 8).astype(np.float32)
        phases = np.random.rand(5).astype(np.float32)  # Wrong size

        with pytest.raises(ValueError, match="batch size mismatch"):
            memory.batch_entangle(vectors, phases)


class TestFractalPELMGPURetrieve:
    """Test retrieve method."""

    def test_retrieve_empty_memory(self) -> None:
        """Test that retrieve returns empty list when memory is empty."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        query = np.random.randn(16).astype(np.float32)
        results = memory.retrieve(query, current_phase=0.5, top_k=5)

        assert results == []

    def test_retrieve_basic(self) -> None:
        """Test basic retrieve operation."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        # Store some vectors
        vectors = np.random.randn(20, 16).astype(np.float32)
        phases = np.random.rand(20).astype(np.float32)
        memory.batch_entangle(vectors, phases)

        # Query with one of the stored vectors
        query = vectors[0]
        results = memory.retrieve(query, current_phase=phases[0], top_k=5)

        assert len(results) == 5
        # Results should be (score, vector, metadata) tuples
        for score, vector, metadata in results:
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0
            assert isinstance(vector, np.ndarray)
            assert vector.shape == (16,)
            assert metadata is None  # No metadata was stored

    def test_retrieve_finds_exact_match(self) -> None:
        """Test that retrieve finds an exact match with high score."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu")

        # Create distinct vectors
        vectors = np.eye(8, dtype=np.float32)  # 8 orthogonal unit vectors
        phases = np.array([0.1 * i for i in range(8)], dtype=np.float32)
        memory.batch_entangle(vectors, phases)

        # Query with vector 0 at phase 0.0
        query = vectors[0]
        results = memory.retrieve(query, current_phase=0.0, top_k=3)

        # First result should be the exact match (high score)
        top_score, top_vector, _ = results[0]
        assert top_score > 0.5  # Should have high score
        np.testing.assert_array_almost_equal(top_vector, query, decimal=5)

    def test_retrieve_with_metadata(self) -> None:
        """Test retrieve returns correct metadata."""
        memory = FractalPELMGPU(dimension=8, capacity=50, device="cpu")

        vectors = np.random.randn(10, 8).astype(np.float32)
        phases = np.random.rand(10).astype(np.float32)
        metadatas = [{"id": i} for i in range(10)]

        memory.batch_entangle(vectors, phases, metadatas)

        # Retrieve
        query = vectors[5]
        results = memory.retrieve(query, current_phase=phases[5], top_k=3)

        # Check that at least one result has metadata
        has_metadata = any(meta is not None for _, _, meta in results)
        assert has_metadata

    def test_retrieve_score_in_valid_range(self) -> None:
        """Test that all scores are in [0, 1] range."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        vectors = np.random.randn(50, 16).astype(np.float32)
        phases = np.random.rand(50).astype(np.float32)
        memory.batch_entangle(vectors, phases)

        # Multiple queries
        for i in range(10):
            query = np.random.randn(16).astype(np.float32)
            results = memory.retrieve(query, current_phase=np.random.rand(), top_k=5)

            for score, _, _ in results:
                assert 0.0 <= score <= 1.0, f"Score {score} out of range"

    def test_retrieve_invalid_query_shape(self) -> None:
        """Test that invalid query shape raises ValueError."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu")

        vectors = np.random.randn(10, 8).astype(np.float32)
        phases = np.random.rand(10).astype(np.float32)
        memory.batch_entangle(vectors, phases)

        # Wrong dimension
        query_wrong_dim = np.random.randn(16).astype(np.float32)
        with pytest.raises(ValueError, match="dimension mismatch"):
            memory.retrieve(query_wrong_dim, current_phase=0.5)

    def test_retrieve_accepts_2d_query(self) -> None:
        """Test that retrieve accepts (1, dim) shaped query."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu")

        vectors = np.random.randn(10, 8).astype(np.float32)
        phases = np.random.rand(10).astype(np.float32)
        memory.batch_entangle(vectors, phases)

        # Query with shape (1, dim)
        query = np.random.randn(1, 8).astype(np.float32)
        results = memory.retrieve(query, current_phase=0.5, top_k=3)

        assert len(results) == 3


class TestFractalPELMGPUBatchRetrieve:
    """Test batch_retrieve method."""

    def test_batch_retrieve_empty_memory(self) -> None:
        """Test batch_retrieve returns empty lists when memory is empty."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        queries = np.random.randn(5, 16).astype(np.float32)
        phases = np.random.rand(5).astype(np.float32)

        results = memory.batch_retrieve(queries, phases, top_k=3)

        assert len(results) == 5
        for query_results in results:
            assert query_results == []

    def test_batch_retrieve_basic(self) -> None:
        """Test basic batch retrieve operation."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        # Store vectors
        vectors = np.random.randn(30, 16).astype(np.float32)
        phases = np.random.rand(30).astype(np.float32)
        memory.batch_entangle(vectors, phases)

        # Batch query
        queries = vectors[:5]
        query_phases = phases[:5]
        results = memory.batch_retrieve(queries, query_phases, top_k=3)

        assert len(results) == 5
        for query_results in results:
            assert len(query_results) == 3
            for score, vector, _ in query_results:
                assert 0.0 <= score <= 1.0
                assert vector.shape == (16,)

    def test_batch_retrieve_shape_mismatch(self) -> None:
        """Test that batch retrieve raises error on shape mismatch."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu")

        vectors = np.random.randn(10, 8).astype(np.float32)
        phases = np.random.rand(10).astype(np.float32)
        memory.batch_entangle(vectors, phases)

        queries = np.random.randn(5, 8).astype(np.float32)
        query_phases = np.random.rand(3).astype(np.float32)  # Mismatch

        with pytest.raises(ValueError, match="batch mismatch"):
            memory.batch_retrieve(queries, query_phases)


class TestFractalPELMGPUReset:
    """Test reset method."""

    def test_reset_clears_memory(self) -> None:
        """Test that reset clears all stored data."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        # Store vectors
        vectors = np.random.randn(20, 16).astype(np.float32)
        phases = np.random.rand(20).astype(np.float32)
        memory.batch_entangle(vectors, phases)

        assert memory.size == 20

        # Reset
        memory.reset()

        assert memory.size == 0

    def test_reset_allows_new_entangle(self) -> None:
        """Test that reset allows new data to be stored."""
        memory = FractalPELMGPU(dimension=8, capacity=10, device="cpu")

        # Fill to capacity
        vectors1 = np.random.randn(10, 8).astype(np.float32)
        phases1 = np.random.rand(10).astype(np.float32)
        memory.batch_entangle(vectors1, phases1)

        assert memory.size == 10

        # Cannot add more
        vectors2 = np.random.randn(5, 8).astype(np.float32)
        phases2 = np.random.rand(5).astype(np.float32)
        with pytest.raises(RuntimeError):
            memory.batch_entangle(vectors2, phases2)

        # After reset, can add again
        memory.reset()
        assert memory.size == 0

        memory.batch_entangle(vectors2, phases2)
        assert memory.size == 5

    def test_reset_retrieve_returns_empty(self) -> None:
        """Test that retrieve returns empty after reset."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        # Store and reset
        vectors = np.random.randn(10, 16).astype(np.float32)
        phases = np.random.rand(10).astype(np.float32)
        memory.batch_entangle(vectors, phases)
        memory.reset()

        # Retrieve should return empty
        query = np.random.randn(16).astype(np.float32)
        results = memory.retrieve(query, current_phase=0.5)

        assert results == []


class TestFractalPELMGPUStateStats:
    """Test get_state_stats method."""

    def test_get_state_stats(self) -> None:
        """Test state stats returns correct information."""
        memory = FractalPELMGPU(
            dimension=16,
            capacity=100,
            device="cpu",
            fractal_weight=0.25,
        )

        stats = memory.get_state_stats()

        assert stats["capacity"] == 100
        assert stats["used"] == 0
        assert "cpu" in stats["device"]
        assert stats["fractal_weight"] == 0.25
        assert "memory_mb" in stats

    def test_state_stats_after_entangle(self) -> None:
        """Test state stats updates after entangle."""
        memory = FractalPELMGPU(dimension=16, capacity=100, device="cpu")

        vectors = np.random.randn(25, 16).astype(np.float32)
        phases = np.random.rand(25).astype(np.float32)
        memory.batch_entangle(vectors, phases)

        stats = memory.get_state_stats()
        assert stats["used"] == 25


class TestFractalPELMGPUNumericalStability:
    """Test numerical stability of scoring."""

    def test_zero_vector_handling(self) -> None:
        """Test handling of zero or near-zero vectors."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu")

        # Include a near-zero vector
        vectors = np.random.randn(10, 8).astype(np.float32)
        vectors[5] = np.zeros(8, dtype=np.float32)  # Zero vector
        phases = np.random.rand(10).astype(np.float32)

        # Should not raise
        memory.batch_entangle(vectors, phases)

        # Query should not produce NaN
        query = np.random.randn(8).astype(np.float32)
        results = memory.retrieve(query, current_phase=0.5, top_k=5)

        for score, _, _ in results:
            assert not np.isnan(score), "Score should not be NaN"
            assert not np.isinf(score), "Score should not be Inf"

    def test_extreme_phase_values(self) -> None:
        """Test with phase values at boundaries."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu")

        vectors = np.random.randn(10, 8).astype(np.float32)
        # Phases at extremes
        phases = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)

        memory.batch_entangle(vectors, phases)

        # Query at extremes
        query = np.random.randn(8).astype(np.float32)

        results_0 = memory.retrieve(query, current_phase=0.0, top_k=5)
        results_1 = memory.retrieve(query, current_phase=1.0, top_k=5)

        # All scores should be valid
        for results in [results_0, results_1]:
            for score, _, _ in results:
                assert 0.0 <= score <= 1.0

    def test_opposite_vectors_score_valid(self) -> None:
        """Test that opposite vectors (cos_sim = -1) still produce valid score in [0,1]."""
        memory = FractalPELMGPU(dimension=4, capacity=10, device="cpu")

        # Create a vector and its opposite
        v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([-1.0, 0.0, 0.0, 0.0], dtype=np.float32)  # Opposite direction

        memory.batch_entangle(
            np.array([v2]),
            np.array([0.5], dtype=np.float32),
        )

        # Query with v1 (opposite to stored v2)
        results = memory.retrieve(v1, current_phase=0.5, top_k=1)

        assert len(results) == 1
        score, _, _ = results[0]
        # Score must still be in [0, 1] even for opposite vectors
        assert 0.0 <= score <= 1.0, f"Score {score} out of valid range"


class TestFractalPELMGPUScoringMonotonicity:
    """Test that scoring behaves correctly with distance and phase differences."""

    def test_score_decreases_with_euclidean_distance(self) -> None:
        """Test that score decreases as Euclidean distance increases (fixed phase)."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu", fractal_weight=0.3)

        # Create base vector
        base = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)

        # Create vectors at increasing distances from base (in same direction)
        # Using positive direction to ensure positive cosine similarity
        vectors = []
        for scale in [1.0, 1.5, 2.0, 3.0, 5.0]:
            vectors.append(base * scale)

        vectors_np = np.array(vectors, dtype=np.float32)
        phases = np.full(len(vectors), 0.5, dtype=np.float32)  # Same phase

        memory.batch_entangle(vectors_np, phases)

        # Query with the base vector at same phase
        results = memory.retrieve(base, current_phase=0.5, top_k=len(vectors))

        # Extract scores
        scores = [score for score, _, _ in results]

        # Verify all scores are in valid range
        for score in scores:
            assert 0.0 <= score <= 1.0, f"Score {score} out of range"

        # The closest vector (scale=1.0, distance=0) should have highest score
        # Note: Due to normalization, vectors in same direction have cos_sim=1
        # but different distances affect the distance_factor
        assert scores[0] >= scores[-1], "Score should not increase with distance"

    def test_score_decreases_with_phase_difference(self) -> None:
        """Test that score decreases as phase difference increases (fixed vector)."""
        memory = FractalPELMGPU(dimension=4, capacity=100, device="cpu", fractal_weight=0.3)

        # Store the same vector with different phases
        base = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
        base = base / np.linalg.norm(base)  # Normalize

        # Create copies with different phases
        phases = np.array([0.0, 0.1, 0.3, 0.5, 0.9], dtype=np.float32)
        vectors = np.tile(base, (len(phases), 1))

        memory.batch_entangle(vectors, phases)

        # Query with same vector at phase 0.0
        results = memory.retrieve(base, current_phase=0.0, top_k=len(phases))

        # Extract scores - they should be sorted descending by score
        scores = [score for score, _, _ in results]

        # First result should have highest score (phase 0.0, exact match)
        # Last result should have lowest score (furthest phase from 0.0)
        assert scores[0] >= scores[-1], "Score should decrease with phase difference"
        # Verify monotonicity: each score should be >= next score
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Scores not monotonic: {scores}"

    def test_identical_vector_and_phase_gives_max_score(self) -> None:
        """Test that identical vector and phase gives score close to 1.0."""
        memory = FractalPELMGPU(dimension=8, capacity=100, device="cpu", fractal_weight=0.3)

        # Create a normalized vector
        vec = np.random.randn(8).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        phase = 0.5

        memory.batch_entangle(np.array([vec]), np.array([phase], dtype=np.float32))

        # Query with exact same vector and phase
        results = memory.retrieve(vec, current_phase=phase, top_k=1)

        assert len(results) == 1
        score, retrieved_vec, _ = results[0]

        # Score should be very close to 1.0 for identical vector and phase
        # With fractal_weight=0.3 and distance=0: distance_factor=1.0
        # cos_sim=1.0, phase_sim=1.0, so score should be 1.0
        assert score > 0.95, f"Expected score near 1.0 for identical match, got {score}"

        # Retrieved vector should match (decimal=3 for float16 storage tolerance)
        # FractalPELMGPU stores vectors in float16 for memory efficiency,
        # which introduces ~1e-3 to 1e-4 precision loss on round-trip
        np.testing.assert_array_almost_equal(retrieved_vec, vec, decimal=3)


class TestFractalPELMGPUTorchImportBehavior:
    """Test import behavior when torch is unavailable."""

    def test_fractal_pelm_raises_runtime_error_when_torch_unavailable(self) -> None:
        """Test that FractalPELMGPU raises RuntimeError with clear message if torch is unavailable.

        This test verifies the error handling by temporarily modifying the module state.
        """
        from mlsdm.memory.experimental import fractal_pelm_gpu

        # Verify TORCH_AVAILABLE is True (since torch is installed)
        assert fractal_pelm_gpu.TORCH_AVAILABLE is True

        # Save original state
        original_available = fractal_pelm_gpu.TORCH_AVAILABLE
        original_msg = getattr(fractal_pelm_gpu, "_IMPORT_ERROR_MSG", None)

        try:
            # Simulate torch not being available
            fractal_pelm_gpu.TORCH_AVAILABLE = False
            # The actual error message is generated during module load,
            # so we set a representative message for testing
            fractal_pelm_gpu._IMPORT_ERROR_MSG = (
                "FractalPELMGPU requires PyTorch. "
                "Install with 'pip install mlsdm[neurolang]' or 'pip install torch>=2.0.0'."
            )

            with pytest.raises(RuntimeError) as exc_info:
                fractal_pelm_gpu.FractalPELMGPU(dimension=8, capacity=10, device="cpu")

            error_msg = str(exc_info.value)
            assert "PyTorch" in error_msg
            assert "mlsdm[neurolang]" in error_msg
        finally:
            # Restore original state
            fractal_pelm_gpu.TORCH_AVAILABLE = original_available
            if original_msg is not None:
                fractal_pelm_gpu._IMPORT_ERROR_MSG = original_msg

    def test_main_mlsdm_package_imports_without_torch(self) -> None:
        """Test that main mlsdm package imports successfully regardless of torch."""
        # This test verifies the main package doesn't break if torch is missing
        # Since torch IS installed in test environment, we just verify import works
        import mlsdm

        assert mlsdm is not None

        # Verify core memory module works
        from mlsdm.memory import PELM, PhaseEntangledLatticeMemory

        assert PhaseEntangledLatticeMemory is not None
        assert PELM is PhaseEntangledLatticeMemory

    def test_experimental_init_exports_fractal_pelm_when_torch_available(self) -> None:
        """Test that __init__.py exports FractalPELMGPU when torch is available."""
        from mlsdm.memory import experimental

        # Should be exported when torch is available
        assert "FractalPELMGPU" in experimental.__all__
        assert hasattr(experimental, "FractalPELMGPU")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
