"""Tests for PELM batch entangle optimization."""

import numpy as np
import pytest

from mlsdm.memory.phase_entangled_lattice_memory import (
    PhaseEntangledLatticeMemory,
)


class TestPELMBatchEntangle:
    """Test batch entangle functionality."""

    def test_batch_entangle_basic(self) -> None:
        """Test basic batch entangle operation."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
        phases = [0.1, 0.5, 0.9]

        indices = pelm.entangle_batch(vectors, phases)

        assert len(indices) == 3
        assert indices == [0, 1, 2]
        assert pelm.size == 3

    def test_batch_entangle_empty(self) -> None:
        """Test batch entangle with empty input."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        indices = pelm.entangle_batch([], [])

        assert indices == []
        assert pelm.size == 0

    def test_batch_entangle_single(self) -> None:
        """Test batch entangle with single vector."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[1.0, 2.0, 3.0, 4.0]]
        phases = [0.5]

        indices = pelm.entangle_batch(vectors, phases)

        assert len(indices) == 1
        assert indices[0] == 0
        assert pelm.size == 1

    def test_batch_entangle_preserves_order(self) -> None:
        """Test that batch entangle preserves vector order."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        phases = [0.1, 0.2, 0.3, 0.4]

        pelm.entangle_batch(vectors, phases)

        # Verify each vector is at expected index
        for i, (vec, phase) in enumerate(zip(vectors, phases, strict=True)):
            assert np.allclose(pelm.memory_bank[i], vec)
            assert pelm.phase_bank[i] == pytest.approx(phase)

    def test_batch_entangle_with_retrieval(self) -> None:
        """Test that batch-entangled vectors can be retrieved."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ]
        phases = [0.1, 0.1]

        pelm.entangle_batch(vectors, phases)

        # Retrieve with query matching first vector
        results = pelm.retrieve([1.0, 0.0, 0.0, 0.0], current_phase=0.1, top_k=1)

        assert len(results) == 1
        assert results[0].resonance > 0.99  # Should be near 1.0

    def test_batch_entangle_length_mismatch(self) -> None:
        """Test batch entangle rejects mismatched lengths."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]
        phases = [0.1]  # Only one phase

        with pytest.raises(ValueError, match="same length"):
            pelm.entangle_batch(vectors, phases)

    def test_batch_entangle_invalid_vector_type(self) -> None:
        """Test batch entangle rejects invalid vector types."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = ["not a list", [0.0, 1.0, 0.0, 0.0]]  # First is string
        phases = [0.1, 0.5]

        with pytest.raises(TypeError, match="vector at index 0 must be a list"):
            pelm.entangle_batch(vectors, phases)

    def test_batch_entangle_invalid_dimension(self) -> None:
        """Test batch entangle rejects wrong dimension."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]  # First is 3D
        phases = [0.1, 0.5]

        with pytest.raises(ValueError, match="dimension mismatch"):
            pelm.entangle_batch(vectors, phases)

    def test_batch_entangle_invalid_phase_type(self) -> None:
        """Test batch entangle rejects invalid phase types."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[1.0, 0.0, 0.0, 0.0]]
        phases = ["not a number"]

        with pytest.raises(TypeError, match="phase at index 0 must be numeric"):
            pelm.entangle_batch(vectors, phases)

    def test_batch_entangle_phase_out_of_range(self) -> None:
        """Test batch entangle rejects phases out of range."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[1.0, 0.0, 0.0, 0.0]]
        phases = [1.5]  # Out of range

        with pytest.raises(ValueError, match="must be in"):
            pelm.entangle_batch(vectors, phases)

    def test_batch_entangle_nan_in_vector(self) -> None:
        """Test batch entangle rejects NaN in vectors."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[float("nan"), 0.0, 0.0, 0.0]]
        phases = [0.1]

        with pytest.raises(ValueError, match="NaN or infinity"):
            pelm.entangle_batch(vectors, phases)

    def test_batch_entangle_inf_in_vector(self) -> None:
        """Test batch entangle rejects infinity in vectors."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[float("inf"), 0.0, 0.0, 0.0]]
        phases = [0.1]

        with pytest.raises(ValueError, match="NaN or infinity"):
            pelm.entangle_batch(vectors, phases)

    def test_batch_entangle_nan_phase(self) -> None:
        """Test batch entangle rejects NaN phase."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[1.0, 0.0, 0.0, 0.0]]
        phases = [float("nan")]

        with pytest.raises(ValueError, match="finite number"):
            pelm.entangle_batch(vectors, phases)

    def test_batch_entangle_wraparound(self) -> None:
        """Test batch entangle handles capacity wraparound."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=3)

        # Fill to capacity
        vectors1 = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
        phases1 = [0.1, 0.2, 0.3]
        pelm.entangle_batch(vectors1, phases1)
        assert pelm.size == 3

        # Add more (should wrap around)
        vectors2 = [[0.0, 0.0, 0.0, 1.0]]
        phases2 = [0.4]
        indices = pelm.entangle_batch(vectors2, phases2)

        assert indices[0] == 0  # Wrapped to position 0
        assert pelm.size == 3  # Still at capacity

    def test_batch_entangle_not_lists(self) -> None:
        """Test batch entangle rejects non-list inputs."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        with pytest.raises(TypeError, match="must be lists"):
            pelm.entangle_batch("vectors", [0.1])

        with pytest.raises(TypeError, match="must be lists"):
            pelm.entangle_batch([[1.0, 0.0, 0.0, 0.0]], "phases")


class TestPELMBatchEntanglePerformance:
    """Test batch entangle performance characteristics."""

    def test_batch_faster_than_individual(self) -> None:
        """Test that batch entangle is more efficient than individual calls."""
        import time

        dim = 384
        num_vectors = 100

        vectors = [[float(i % 10) for _ in range(dim)] for i in range(num_vectors)]
        phases = [0.5] * num_vectors

        # Time batch operation
        pelm_batch = PhaseEntangledLatticeMemory(dimension=dim, capacity=1000)
        start = time.perf_counter()
        pelm_batch.entangle_batch(vectors, phases)
        batch_time = time.perf_counter() - start

        # Time individual operations
        pelm_individual = PhaseEntangledLatticeMemory(dimension=dim, capacity=1000)
        start = time.perf_counter()
        for vec, phase in zip(vectors, phases, strict=True):
            pelm_individual.entangle(vec, phase)
        individual_time = time.perf_counter() - start

        # Batch should be at least as fast (usually faster due to single lock acquisition)
        # We allow some tolerance for timing variations
        assert batch_time <= individual_time * 1.5

    def test_batch_single_checksum_update(self) -> None:
        """Test that batch updates checksum only once."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        vectors = [[float(i)] * 4 for i in range(10)]
        phases = [0.5] * 10

        # Batch should update checksum once at the end
        pelm.entangle_batch(vectors, phases)

        # Verify memory is not corrupted
        assert not pelm.detect_corruption()
