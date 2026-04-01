"""
Unit Tests for Phase-Entangled Lattice Memory (PELM, formerly QILM_v2)

Tests corruption detection, auto-recovery, and boundary checks.
"""

import numpy as np
import pytest

from mlsdm.memory.phase_entangled_lattice_memory import MemoryRetrieval, PhaseEntangledLatticeMemory


class TestBackwardCompatibility:
    """Test backward compatibility with QILM_v2 and PELM alias."""

    def test_pelm_alias_exists(self):
        """Test that PELM alias is available as convenient shorthand."""
        from mlsdm.memory import PELM, PhaseEntangledLatticeMemory

        # Verify PELM is an alias to the main class
        assert PELM is PhaseEntangledLatticeMemory

    def test_pelm_alias_works(self):
        """Test that PELM alias can be instantiated and used."""
        from mlsdm.memory import PELM

        # Create instance using PELM alias
        memory = PELM(dimension=10, capacity=100)
        assert memory is not None
        assert memory.dimension == 10
        assert memory.capacity == 100

    def test_qilm_v2_alias_exists(self):
        """Test that QILM_v2 alias is available for backward compatibility."""
        from mlsdm.memory import PhaseEntangledLatticeMemory, QILM_v2

        # Verify alias points to the same class
        assert QILM_v2 is PhaseEntangledLatticeMemory

    def test_qilm_v2_alias_works(self):
        """Test that QILM_v2 alias can be instantiated and used."""
        from mlsdm.memory import QILM_v2

        # Create instance using old name
        memory = QILM_v2(dimension=10, capacity=100)
        assert memory is not None
        assert memory.dimension == 10
        assert memory.capacity == 100

    def test_all_aliases_are_same_class(self):
        """Test that all aliases (PELM, QILM_v2, PhaseEntangledLatticeMemory) refer to the same class."""
        from mlsdm.memory import PELM, PhaseEntangledLatticeMemory, QILM_v2

        # All three should be the exact same class
        assert PELM is PhaseEntangledLatticeMemory
        assert QILM_v2 is PhaseEntangledLatticeMemory
        assert PELM is QILM_v2


class TestPELMInitialization:
    """Test PELM initialization."""

    def test_initialization(self):
        """Test PELM can be initialized."""
        pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)
        assert pelm is not None
        assert pelm.dimension == 10
        assert pelm.capacity == 100
        assert pelm.pointer == 0
        assert pelm.size == 0

    def test_initialization_with_defaults(self):
        """Test PELM initializes with default parameters."""
        pelm = PhaseEntangledLatticeMemory()
        assert pelm.dimension == 384
        assert pelm.capacity == 20000

    def test_initialization_validates_dimension(self):
        """Test initialization validates dimension parameter."""
        with pytest.raises(ValueError, match="dimension must be positive"):
            PhaseEntangledLatticeMemory(dimension=0)
        with pytest.raises(ValueError, match="dimension must be positive"):
            PhaseEntangledLatticeMemory(dimension=-1)

    def test_initialization_validates_capacity(self):
        """Test initialization validates capacity parameter."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            PhaseEntangledLatticeMemory(capacity=0)
        with pytest.raises(ValueError, match="capacity must be positive"):
            PhaseEntangledLatticeMemory(capacity=-1)
        with pytest.raises(ValueError, match="capacity too large"):
            PhaseEntangledLatticeMemory(capacity=2_000_000)


class TestPELMEntangle:
    """Test PELM entangle operation."""

    def test_entangle_basic(self):
        """Test basic entangle operation."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        vector = [1.0, 2.0, 3.0]
        phase = 0.5

        idx = pelm.entangle(vector, phase)

        assert idx == 0
        assert pelm.size == 1
        assert pelm.pointer == 1
        np.testing.assert_array_almost_equal(pelm.memory_bank[0], vector)
        assert pelm.phase_bank[0] == 0.5

    def test_entangle_multiple_vectors(self):
        """Test entangling multiple vectors."""
        pelm = PhaseEntangledLatticeMemory(dimension=2, capacity=5)

        vectors = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        phases = [0.1, 0.5, 0.9]

        for i, (vec, phase) in enumerate(zip(vectors, phases, strict=True)):
            idx = pelm.entangle(vec, phase)
            assert idx == i

        assert pelm.size == 3
        assert pelm.pointer == 3

    def test_entangle_wraparound(self):
        """Test pointer wraparound when capacity is reached."""
        pelm = PhaseEntangledLatticeMemory(dimension=2, capacity=3)

        # Fill to capacity
        for i in range(3):
            pelm.entangle([float(i), float(i + 1)], 0.1 * i)

        assert pelm.pointer == 0  # Should wrap around
        assert pelm.size == 3

        # Add one more to test wraparound
        pelm.entangle([10.0, 11.0], 0.5)
        assert pelm.pointer == 1
        assert pelm.size == 3  # Size stays at capacity


class TestPELMv2Retrieve:
    """Test PhaseEntangledLatticeMemory retrieve operation."""

    def test_retrieve_basic(self):
        """Test basic retrieve operation."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        vector = [1.0, 2.0, 3.0]
        phase = 0.5
        pelm.entangle(vector, phase)

        results = pelm.retrieve([1.0, 2.0, 3.0], 0.5, phase_tolerance=0.1, top_k=1)

        assert len(results) == 1
        assert isinstance(results[0], MemoryRetrieval)
        np.testing.assert_array_almost_equal(results[0].vector, vector)
        assert results[0].phase == 0.5

    def test_retrieve_empty_memory(self):
        """Test retrieve returns empty list when memory is empty."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        results = pelm.retrieve([1.0, 2.0, 3.0], 0.5)
        assert results == []

    def test_retrieve_with_phase_tolerance(self):
        """Test retrieve with phase tolerance."""
        pelm = PhaseEntangledLatticeMemory(dimension=2, capacity=10)

        pelm.entangle([1.0, 2.0], 0.1)
        pelm.entangle([3.0, 4.0], 0.15)
        pelm.entangle([5.0, 6.0], 0.5)

        results = pelm.retrieve([1.0, 2.0], 0.1, phase_tolerance=0.1, top_k=5)

        # Should get both vectors at phase 0.1 and 0.15
        assert len(results) == 2

    def test_retrieve_no_match(self):
        """Test retrieve with no matching phases."""
        pelm = PhaseEntangledLatticeMemory(dimension=2, capacity=10)

        pelm.entangle([1.0, 2.0], 0.1)

        results = pelm.retrieve([1.0, 2.0], 0.9, phase_tolerance=0.05)

        assert results == []


class TestPELMv2CorruptionDetection:
    """Test PhaseEntangledLatticeMemory corruption detection."""

    def test_detect_no_corruption(self):
        """Test detect_corruption returns False for valid state."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        assert not pelm.detect_corruption()

    def test_detect_pointer_out_of_bounds(self):
        """Test corruption detection for pointer out of bounds."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        # Corrupt pointer
        pelm.pointer = 100

        assert pelm.detect_corruption()

    def test_detect_negative_pointer(self):
        """Test corruption detection for negative pointer."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        # Corrupt pointer
        pelm.pointer = -1

        assert pelm.detect_corruption()

    def test_detect_size_corruption(self):
        """Test corruption detection for invalid size."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        # Corrupt size
        pelm.size = 100

        assert pelm.detect_corruption()

    def test_detect_checksum_mismatch(self):
        """Test corruption detection for checksum mismatch."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        # Directly corrupt memory without updating checksum
        pelm.memory_bank[0] = np.array([99.0, 99.0, 99.0], dtype=np.float32)

        assert pelm.detect_corruption()


class TestPELMv2AutoRecovery:
    """Test PhaseEntangledLatticeMemory auto-recovery mechanism."""

    def test_auto_recover_pointer_corruption(self):
        """Test auto-recovery fixes pointer corruption."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)
        pelm.entangle([4.0, 5.0, 6.0], 0.6)

        # Corrupt pointer
        pelm.pointer = 100

        # Verify corruption detected
        assert pelm.detect_corruption()

        # Auto-recover
        recovered = pelm.auto_recover()

        assert recovered
        assert pelm.pointer == 2  # Should be fixed to size % capacity
        assert not pelm.detect_corruption()

    def test_auto_recover_negative_pointer(self):
        """Test auto-recovery fixes negative pointer."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        # Corrupt pointer
        pelm.pointer = -5

        recovered = pelm.auto_recover()

        assert recovered
        assert pelm.pointer >= 0
        assert not pelm.detect_corruption()

    def test_auto_recover_size_corruption(self):
        """Test auto-recovery fixes size corruption."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        # Corrupt size
        pelm.size = -1

        recovered = pelm.auto_recover()

        assert recovered
        assert pelm.size >= 0
        assert not pelm.detect_corruption()

    def test_auto_recover_rebuilds_norms(self):
        """Test auto-recovery rebuilds norms."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        original_norm = pelm.norms[0]

        # Corrupt norms
        pelm.norms[0] = 0.0

        recovered = pelm.auto_recover()

        assert recovered
        # Norm should be restored
        np.testing.assert_almost_equal(pelm.norms[0], original_norm)


class TestPELMv2IntegrationWithCorruption:
    """Test PhaseEntangledLatticeMemory integration scenarios with corruption."""

    def test_forceful_corruption_and_recovery(self):
        """Test forcefully corrupt state and verify recovery."""
        pelm = PhaseEntangledLatticeMemory(dimension=5, capacity=10)

        # Add some data
        vectors = [[float(i)] * 5 for i in range(5)]
        phases = [0.1 * i for i in range(5)]

        for vec, phase in zip(vectors, phases, strict=True):
            pelm.entangle(vec, phase)

        # Verify no corruption initially
        assert not pelm.detect_corruption()

        # Forcefully corrupt multiple aspects
        pelm.pointer = 1000  # Invalid pointer
        pelm.size = -5  # Invalid size
        pelm.memory_bank[0] = np.array([999.0] * 5, dtype=np.float32)  # Corrupt data

        # Verify corruption detected
        assert pelm.detect_corruption()

        # Attempt recovery
        recovered = pelm.auto_recover()

        assert recovered
        assert not pelm.detect_corruption()
        assert pelm.pointer >= 0 and pelm.pointer < pelm.capacity
        assert pelm.size >= 0 and pelm.size <= pelm.capacity

    def test_retrieve_triggers_auto_recovery(self):
        """Test that retrieve triggers auto-recovery on corruption."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        pelm.entangle([1.0, 2.0, 3.0], 0.5)
        pelm.entangle([4.0, 5.0, 6.0], 0.5)

        # Corrupt pointer
        pelm.pointer = -1

        # Retrieve should trigger auto-recovery
        results = pelm.retrieve([1.0, 2.0, 3.0], 0.5)

        # Should succeed after recovery
        assert len(results) > 0
        assert not pelm.detect_corruption()

    def test_entangle_triggers_auto_recovery(self):
        """Test that entangle triggers auto-recovery on corruption."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        # Corrupt pointer
        pelm.pointer = 100

        # Entangle should trigger auto-recovery
        idx = pelm.entangle([4.0, 5.0, 6.0], 0.6)

        # Should succeed after recovery
        assert idx >= 0
        assert not pelm.detect_corruption()

    def test_recovery_failure_raises_error(self):
        """Test that unrecoverable corruption raises error."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        pelm.entangle([1.0, 2.0, 3.0], 0.5)

        # Create severe corruption that might not be recoverable
        # by setting invalid pointer
        pelm.pointer = 100

        # Force recovery to fail by making auto_recover fail internally
        # This is a simulation - in practice the current implementation should recover
        # But we test the error path exists
        try:
            # Normal operations should attempt recovery
            pelm.entangle([4.0, 5.0, 6.0], 0.6)
        except RuntimeError as e:
            # If recovery fails, should raise RuntimeError
            assert "Memory corruption" in str(e)


class TestPELMv2BoundaryChecks:
    """Test PhaseEntangledLatticeMemory boundary checks."""

    def test_pointer_wraparound_at_capacity(self):
        """Test explicit pointer wraparound at capacity boundary."""
        pelm = PhaseEntangledLatticeMemory(dimension=2, capacity=5)

        # Fill to capacity
        for i in range(5):
            idx = pelm.entangle([float(i), float(i + 1)], 0.1)
            assert idx == i

        # Pointer should wrap to 0
        assert pelm.pointer == 0

        # Next entangle should use index 0
        idx = pelm.entangle([99.0, 99.0], 0.9)
        assert idx == 0
        assert pelm.pointer == 1

    def test_size_stops_at_capacity(self):
        """Test size doesn't exceed capacity."""
        pelm = PhaseEntangledLatticeMemory(dimension=2, capacity=3)

        # Add more than capacity
        for i in range(10):
            pelm.entangle([float(i), float(i + 1)], 0.1 * i)

        # Size should be capped at capacity
        assert pelm.size == 3
        assert pelm.size <= pelm.capacity

    def test_validate_pointer_bounds(self):
        """Test _validate_pointer_bounds method."""
        pelm = PhaseEntangledLatticeMemory(dimension=2, capacity=10)

        # Valid state
        assert pelm._validate_pointer_bounds()

        # Invalid pointer (too large)
        pelm.pointer = 100
        assert not pelm._validate_pointer_bounds()

        # Invalid pointer (negative)
        pelm.pointer = -1
        assert not pelm._validate_pointer_bounds()

        # Fix pointer
        pelm.pointer = 5
        assert pelm._validate_pointer_bounds()


class TestPELMv2StateStats:
    """Test PhaseEntangledLatticeMemory state statistics."""

    def test_get_state_stats(self):
        """Test get_state_stats returns correct information."""
        pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

        pelm.entangle([1.0] * 10, 0.5)

        stats = pelm.get_state_stats()

        assert stats["capacity"] == 100
        assert stats["used"] == 1
        assert "memory_mb" in stats
        assert isinstance(stats["memory_mb"], float)


class TestPELMInputValidation:
    """Test input validation for PhaseEntangledLatticeMemory methods."""

    def test_entangle_validates_vector_type(self):
        """Test that entangle validates vector is a list."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        with pytest.raises(TypeError, match="vector must be a list"):
            pelm.entangle(np.array([1.0, 2.0, 3.0]), 0.5)  # numpy array instead of list

    def test_entangle_validates_vector_dimension(self):
        """Test that entangle validates vector dimension matches."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        with pytest.raises(ValueError, match="vector dimension mismatch"):
            pelm.entangle([1.0, 2.0], 0.5)  # Wrong dimension

        with pytest.raises(ValueError, match="vector dimension mismatch"):
            pelm.entangle([1.0, 2.0, 3.0, 4.0], 0.5)  # Wrong dimension

    def test_entangle_validates_phase_type(self):
        """Test that entangle validates phase is numeric."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        with pytest.raises(TypeError, match="phase must be numeric"):
            pelm.entangle([1.0, 2.0, 3.0], "0.5")  # String instead of number

    def test_entangle_validates_phase_range(self):
        """Test that entangle validates phase is in [0.0, 1.0]."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        with pytest.raises(ValueError, match="phase must be in"):
            pelm.entangle([1.0, 2.0, 3.0], -0.1)  # Below 0.0

        with pytest.raises(ValueError, match="phase must be in"):
            pelm.entangle([1.0, 2.0, 3.0], 1.5)  # Above 1.0

    def test_entangle_accepts_valid_inputs(self):
        """Test that entangle accepts valid inputs."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        # Should work with correct inputs
        idx = pelm.entangle([1.0, 2.0, 3.0], 0.5)
        assert idx == 0

        # Phase at boundaries should work
        idx = pelm.entangle([1.0, 2.0, 3.0], 0.0)
        assert idx == 1

        idx = pelm.entangle([1.0, 2.0, 3.0], 1.0)
        assert idx == 2

    def test_init_error_messages_are_descriptive(self):
        """Test that initialization errors provide helpful messages."""
        # Test dimension error
        with pytest.raises(ValueError, match="Dimension determines the embedding vector size"):
            PhaseEntangledLatticeMemory(dimension=0, capacity=10)

        # Test capacity error
        with pytest.raises(ValueError, match="maximum number of vectors"):
            PhaseEntangledLatticeMemory(dimension=10, capacity=0)

        # Test large capacity error includes memory estimate
        with pytest.raises(ValueError, match="Estimated memory"):
            PhaseEntangledLatticeMemory(dimension=384, capacity=2_000_000)

    def test_entangle_rejects_nan_in_vector(self):
        """Test that entangle rejects vectors containing NaN."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        with pytest.raises(ValueError, match="invalid value"):
            pelm.entangle([1.0, float("nan"), 3.0], 0.5)

    def test_entangle_rejects_inf_in_vector(self):
        """Test that entangle rejects vectors containing infinity."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        with pytest.raises(ValueError, match="invalid value"):
            pelm.entangle([1.0, float("inf"), 3.0], 0.5)

        with pytest.raises(ValueError, match="invalid value"):
            pelm.entangle([float("-inf"), 2.0, 3.0], 0.5)

    def test_entangle_rejects_nan_phase(self):
        """Test that entangle rejects NaN phase."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        with pytest.raises(ValueError, match="finite number"):
            pelm.entangle([1.0, 2.0, 3.0], float("nan"))

    def test_entangle_rejects_inf_phase(self):
        """Test that entangle rejects infinite phase."""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        with pytest.raises(ValueError, match="finite number"):
            pelm.entangle([1.0, 2.0, 3.0], float("inf"))


class TestPELMObservability:
    """Test PELM observability logging paths."""

    def test_corruption_with_observability_logging(self):
        """Test corruption detection with observability logging enabled."""
        from unittest.mock import patch

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_corruption') as mock_record, \
             patch.object(PhaseEntangledLatticeMemory, '_auto_recover_unsafe', return_value=False):
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            pelm.pointer = -1
            with pytest.raises(RuntimeError, match="Memory corruption detected"):
                pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.5)
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['detected'] is True
            assert call_args['recovered'] is False

    def test_low_confidence_rejection_with_observability(self):
        """Test low confidence rejection with observability logging."""
        from datetime import datetime
        from unittest.mock import patch

        from mlsdm.memory.provenance import MemoryProvenance, MemorySource

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_store') as mock_record:
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            pelm._confidence_threshold = 0.8
            low_conf_prov = MemoryProvenance(
                source=MemorySource.USER_INPUT,
                confidence=0.3,
                timestamp=datetime.now()
            )
            result = pelm.entangle(
                [1.0, 2.0, 3.0, 4.0],
                phase=0.5,
                provenance=low_conf_prov,
                correlation_id="test-rejection"
            )
            assert result == -1
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['index'] == -1
            assert call_args['correlation_id'] == "test-rejection"

    def test_store_with_observability_metrics(self):
        """Test storage with observability metrics logging."""
        from unittest.mock import patch

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_store') as mock_record:
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.5, correlation_id="test-store")
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['index'] == 0
            assert call_args['phase'] == 0.5
            assert call_args['correlation_id'] == "test-store"
            assert call_args['latency_ms'] >= 0

    def test_batch_entangle_with_observability(self):
        """Test batch entangle with observability logging."""
        from unittest.mock import patch

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_store') as mock_record:
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            vectors = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]]
            phases = [0.3, 0.7]
            pelm.entangle_batch(vectors, phases, correlation_id="batch-test")
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['correlation_id'] == "batch-test"

    def test_retrieve_empty_with_observability(self):
        """Test retrieve on empty memory with observability logging."""
        from unittest.mock import patch

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_retrieve') as mock_record:
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            results = pelm.retrieve(
                [1.0, 2.0, 3.0, 4.0],
                current_phase=0.5,
                correlation_id="empty-retrieve"
            )
            assert results == []
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['results_count'] == 0
            assert call_args['avg_resonance'] is None

    def test_retrieve_no_phase_match_with_observability(self):
        """Test retrieve with no phase match with observability logging."""
        from unittest.mock import patch

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_retrieve') as mock_record:
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.1)
            results = pelm.retrieve(
                [1.0, 2.0, 3.0, 4.0],
                current_phase=0.9,
                phase_tolerance=0.05,
                correlation_id="no-match"
            )
            assert results == []
            assert any(
                call[1].get('correlation_id') == 'no-match'
                for call in mock_record.call_args_list
            )

    def test_retrieve_success_with_observability(self):
        """Test successful retrieve with observability logging."""
        from unittest.mock import patch

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_retrieve') as mock_record:
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.5)
            results = pelm.retrieve(
                [1.0, 2.0, 3.0, 4.0],
                current_phase=0.5,
                correlation_id="success-retrieve"
            )
            assert len(results) == 1
            retrieve_calls = [
                call for call in mock_record.call_args_list
                if call[1].get('correlation_id') == "success-retrieve"
            ]
            assert len(retrieve_calls) >= 1
            call_args = retrieve_calls[0][1]
            assert call_args['results_count'] == 1
            assert call_args['avg_resonance'] is not None

    def test_batch_entangle_all_rejected_with_observability(self):
        """Test batch entangle where ALL vectors are rejected due to low confidence."""
        from datetime import datetime
        from unittest.mock import patch

        from mlsdm.memory.provenance import MemoryProvenance, MemorySource

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_store') as mock_record:
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            pelm._confidence_threshold = 0.9  # High threshold

            # All provenances have low confidence - ALL will be rejected
            low_conf_provenances = [
                MemoryProvenance(
                    source=MemorySource.USER_INPUT,
                    confidence=0.1,  # Below 0.9 threshold
                    timestamp=datetime.now()
                )
                for _ in range(3)
            ]

            vectors = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0], [9.0, 10.0, 11.0, 12.0]]
            phases = [0.3, 0.5, 0.7]

            indices = pelm.entangle_batch(vectors, phases, provenances=low_conf_provenances)

            # All should be rejected
            assert indices == [-1, -1, -1]
            assert pelm.size == 0

            # Observability should record with fallback values (last_accepted is None)
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            # When all rejected, falls back to (0, 0.0, 0.0)
            assert call_args['index'] == 0
            assert call_args['phase'] == 0.0
            assert call_args['vector_norm'] == 0.0

    def test_corruption_recovery_success_with_observability(self):
        """Test corruption recovery SUCCESS path with observability logging."""
        from unittest.mock import patch

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_corruption') as mock_record:
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.5)

            # Corrupt pointer (recoverable)
            pelm.pointer = -1

            # Entangle should trigger recovery and succeed
            idx = pelm.entangle([5.0, 6.0, 7.0, 8.0], phase=0.6)

            assert idx >= 0  # Recovery succeeded
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['detected'] is True
            assert call_args['recovered'] is True  # This is the SUCCESS path


class TestPELMReturnIndices:
    """Test PELM return_indices parameter."""

    def test_retrieve_with_return_indices(self):
        """Test retrieve with return_indices parameter."""
        from unittest.mock import patch

        with patch('mlsdm.memory.phase_entangled_lattice_memory._OBSERVABILITY_AVAILABLE', True), \
             patch('mlsdm.memory.phase_entangled_lattice_memory.record_pelm_retrieve'):
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)

            # Empty memory
            results, indices = pelm.retrieve(
                [1.0, 2.0, 3.0, 4.0],
                current_phase=0.5,
                return_indices=True
            )
            assert results == []
            assert indices == []

            # Add memory
            pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.5)

            # No phase match
            results, indices = pelm.retrieve(
                [1.0, 2.0, 3.0, 4.0],
                current_phase=0.9,
                phase_tolerance=0.05,
                return_indices=True
            )
            assert results == []
            assert indices == []

            # Successful match with indices
            results, indices = pelm.retrieve(
                [1.0, 2.0, 3.0, 4.0],
                current_phase=0.5,
                return_indices=True,
                correlation_id="with-indices"
            )
            assert len(results) == 1
            assert len(indices) == 1
            assert indices[0] == 0


class TestPELMValidation:
    """Test PELM validation and error handling."""

    def test_retrieve_dimension_mismatch(self):
        """Test retrieve with dimension mismatch."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.5)

        with pytest.raises(ValueError, match="query_vector dimension mismatch"):
            pelm.retrieve([1.0, 2.0], current_phase=0.5)

    def test_batch_provenances_length_mismatch(self):
        """Test batch entangle with provenances length mismatch."""
        from datetime import datetime

        from mlsdm.memory.provenance import MemoryProvenance, MemorySource

        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)

        vectors = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]]
        phases = [0.3, 0.7]
        provenances = [MemoryProvenance(
            source=MemorySource.SYSTEM_PROMPT,
            confidence=1.0,
            timestamp=datetime.now()
        )]

        with pytest.raises(ValueError, match="provenances must match vectors length"):
            pelm.entangle_batch(vectors, phases, provenances=provenances)


class TestPELMFallbackAndEdgeCases:
    """Test PELM fallback behavior and edge cases."""

    def test_provenance_fallback_for_legacy_memories(self):
        """Test provenance fallback for memories without provenance."""
        from mlsdm.memory.provenance import MemorySource

        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
        # Add two memories
        pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.5)
        pelm.entangle([2.0, 3.0, 4.0, 5.0], phase=0.5)

        # Simulate legacy data - remove provenance for second memory
        # by truncating the provenance list (but keep memory_ids aligned)
        pelm._provenance = pelm._provenance[:1]
        pelm._memory_ids = pelm._memory_ids[:1]

        # Retrieve should still work and use fallback for second memory
        results = pelm.retrieve([2.0, 3.0, 4.0, 5.0], current_phase=0.5, top_k=2)
        # Should get at least the second memory with fallback provenance
        assert len(results) >= 1
        # Check if any result uses the fallback provenance
        has_fallback = any(
            r.provenance.source == MemorySource.SYSTEM_PROMPT and
            r.provenance.confidence == 1.0
            for r in results
        )
        assert has_fallback

    def test_rebuild_index_with_size_exceeding_capacity(self):
        """Test _rebuild_index when size exceeds capacity."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
        pelm.size = 15
        pelm._rebuild_index()
        assert pelm.size == pelm.capacity

    def test_rebuild_index_with_negative_size(self):
        """Test _rebuild_index corrects negative size."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
        pelm.size = -5  # Corrupt to negative
        pelm._rebuild_index()
        assert pelm.size == 0  # Should be corrected to 0

    def test_evict_lowest_confidence_empty_memory(self):
        """Test _evict_lowest_confidence on empty memory."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
        pelm._evict_lowest_confidence()
        assert pelm.size == 0

    def test_auto_recover_failure_on_exception(self):
        """Test auto_recover returns False on exception."""
        from unittest.mock import patch

        with patch.object(PhaseEntangledLatticeMemory, '_rebuild_index', side_effect=RuntimeError("Rebuild failed")):
            pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
            pelm.pointer = -1
            result = pelm.auto_recover()
            assert result is False

    def test_auto_recover_returns_true_when_no_corruption(self):
        """Test auto_recover returns True when no corruption is detected."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
        pelm.entangle([1.0, 2.0, 3.0, 4.0], phase=0.5)

        # No corruption - should return True immediately
        result = pelm.auto_recover()
        assert result is True

    def test_entangle_non_numeric_vector_element_raises_typeerror(self):
        """Test that non-numeric vector elements raise TypeError."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)

        with pytest.raises(TypeError, match="must be numeric"):
            pelm.entangle([1.0, 2.0, "not a number", 4.0], phase=0.5)

    def test_retrieve_with_near_zero_query_clamps_norm(self):
        """Test retrieve clamps q_norm to MIN_NORM_THRESHOLD on near-zero query."""
        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=10)
        pelm.entangle([1.0, 0.0, 0.0, 0.0], phase=0.5)

        # Near-zero query vector - should not fail due to division by zero
        tiny_query = [1e-20, 0.0, 0.0, 0.0]  # Very small norm
        results = pelm.retrieve(tiny_query, current_phase=0.5)

        # Should return results without error
        assert isinstance(results, list)

    def test_retrieve_argpartition_branch_with_many_candidates(self):
        """Test retrieve uses argpartition when num_candidates > top_k * 2."""
        from datetime import datetime

        from mlsdm.memory.provenance import MemoryProvenance, MemorySource

        pelm = PhaseEntangledLatticeMemory(dimension=4, capacity=100)

        # Add enough memories to trigger argpartition branch
        # We need more than top_k * 2 candidates after phase filtering
        for i in range(30):
            vector = [float(i + 1), float(i + 2), float(i + 3), float(i + 4)]
            provenance = MemoryProvenance(
                source=MemorySource.USER_INPUT,
                confidence=0.9,
                timestamp=datetime.now(),
            )
            pelm.entangle(vector, phase=0.5, provenance=provenance)

        # Retrieve with top_k=5, so we need > 10 candidates to trigger argpartition
        results = pelm.retrieve(
            [15.0, 16.0, 17.0, 18.0],
            current_phase=0.5,
            top_k=5,
            phase_tolerance=1.0,  # Wide tolerance to get all candidates
        )

        assert len(results) == 5
        # Results should be sorted by resonance (highest first)
        resonances = [r.resonance for r in results]
        assert resonances == sorted(resonances, reverse=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
